"""Views for the node settings page."""
# -*- coding: utf-8 -*-
from rest_framework import status as http_status

from framework.auth.decorators import must_be_logged_in
from flask import request

from addons.base import generic_views
from addons.datasteward.serializer import DataStewardSerializer
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, DatabaseError, IntegrityError
from osf.utils.permissions import ADMIN
from osf.exceptions import NodeStateError

import logging

logger = logging.getLogger(__name__)

SHORT_NAME = 'datasteward'
FULL_NAME = 'DataSteward'
OSF_NODE = 'osf.node'

datasteward_get_config = generic_views.get_config(
    SHORT_NAME,
    DataStewardSerializer
)


@must_be_logged_in
def datasteward_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of DataSteward user settings"""
    addon_user_settings = auth.user.get_addon(SHORT_NAME)

    return {
        'enabled': addon_user_settings.enabled if addon_user_settings else False,
    }, http_status.HTTP_200_OK


@must_be_logged_in
def datasteward_user_config_post(auth, **kwargs):
    data = request.get_json()
    enabled = data.get('enabled', None)
    if enabled is None or not isinstance(enabled, bool):
        # If request's 'enabled' field is not valid then return HTTP 400
        return {}, http_status.HTTP_400_BAD_REQUEST

    if not auth.user.is_data_steward:
        # If user is not a DataSteward then return HTTP 403
        return {}, http_status.HTTP_403_FORBIDDEN

    addon_user_settings = auth.user.get_addon(SHORT_NAME)
    if not addon_user_settings:
        # Failsafe: If user does not have DataSteward add-on settings then return HTTP 403
        return {}, http_status.HTTP_403_FORBIDDEN

    # Update add-on user settings
    addon_user_settings.enabled = enabled
    addon_user_settings.save()

    if enabled:
        # 4.2.2: Enable DataSteward addon process
        result = enable_datasteward_addon(auth)

        if not result:
            return {}, http_status.HTTP_500_INTERNAL_SERVER_ERROR

        return {}, http_status.HTTP_200_OK
    else:
        # 4.2.4: Disable DataSteward addon process
        skipped_projects = disable_datasteward_addon(auth)

        if skipped_projects is None:
            return {}, http_status.HTTP_500_INTERNAL_SERVER_ERROR

        response_body = [{'guid': project._id, 'name': project.title} for project in skipped_projects]

        return {'skipped_projects': response_body}, http_status.HTTP_200_OK


def enable_datasteward_addon(auth, is_from_auth=False, **kwargs):
    # Check if user has any affiliated institutions
    user = auth.user
    institutions = user.affiliated_institutions.all()
    if not institutions:
        return False

    # Get projects from institutions
    with transaction.atomic():
        for institution in institutions:
            # Get projects from institution
            projects = institution.nodes.filter(type=OSF_NODE, is_deleted=False)
            for project in projects:
                try:
                    if not project.is_contributor(user):
                        # If user is not project's contributor then add user to contributor list
                        result = project.add_contributor(user, permissions=ADMIN, visible=True, send_email=None,
                                                         auth=auth, log=True, save=False)
                        if result:
                            contributor = project.contributor_class.objects.get(user=user, node=project)
                            contributor.is_data_steward = True
                            contributor.save()
                    else:
                        # Otherwise, promote user's permission to Project Administrator
                        contributor = project.contributor_class.objects.get(user=user, node=project)
                        if not contributor.is_data_steward:
                            # If user is not already a data steward then set data steward role to user and save old permission for later recovery
                            contributor.is_data_steward = True
                            contributor.data_steward_old_permission = contributor.permission
                        project.update_contributor(user, permission=ADMIN, visible=True, auth=auth, save=False, admin_check=False)
                        contributor.save()
                except (DatabaseError, IntegrityError) as e:
                    # If error occurred while manipulating DB then ignore it
                    logger.warning(e)
                except Exception as e:
                    # If currently running on "Configure add-on accounts" screen then throws error
                    # Otherwise, ignore it
                    if not is_from_auth:
                        raise e

    return True


def disable_datasteward_addon(auth, **kwargs):
    # Check if user has any affiliated institutions
    user = auth.user
    institutions = user.affiliated_institutions.all()
    if not institutions:
        return None

    # Get projects from institutions
    skipped_projects = []
    for institution in institutions:
        # Get projects from institution
        projects = institution.nodes.filter(type=OSF_NODE, is_deleted=False)
        for project in projects:
            try:
                # If user is not contributor of project then skip
                if not project.is_contributor(user):
                    continue

                contributor = project.contributor_class.objects.get(user=user, node=project)

                # If user is not data steward of project then skip
                if not contributor.is_data_steward:
                    continue

                if contributor.data_steward_old_permission is not None:
                    # If user had contributor's permission in project then restore that permission
                    project.update_contributor(user, permission=contributor.data_steward_old_permission, visible=True,
                                               auth=auth, save=False, admin_check=False)
                    contributor.is_data_steward = False
                    contributor.data_steward_old_permission = None
                    contributor.save()
                else:
                    # Otherwise, remove user from project's contributor list
                    result = project.remove_contributor(user, auth=auth)
                    if not result:
                        skipped_projects.append(project)
            except (DatabaseError, IntegrityError, NodeStateError, ObjectDoesNotExist) as e:
                # If DatabaseError, IntegrityError, NodeStateError or ObjectDoesNotExist are raised
                # Log warning, add project to skipped project list
                logger.warning(e)
                skipped_projects.append(project)

    return skipped_projects
