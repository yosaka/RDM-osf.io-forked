"""Views for the add-on's user settings page."""
# -*- coding: utf-8 -*-
from rest_framework import status as http_status

from framework.auth.decorators import must_be_logged_in
from flask import request

from django.db import transaction
from osf.utils.permissions import ADMIN

import logging

logger = logging.getLogger(__name__)

SHORT_NAME = 'datasteward'
OSF_NODE = 'osf.node'


@must_be_logged_in
def datasteward_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of DataSteward user settings"""
    user = auth.user
    addon_user_settings = user.get_addon(SHORT_NAME)
    addon_user_settings_enabled = addon_user_settings.enabled if addon_user_settings else False

    # If user is not a data steward and does not have add-on enabled before, return HTTP 403
    if not user.is_data_steward and not addon_user_settings_enabled:
        return {}, http_status.HTTP_403_FORBIDDEN

    return {
        'enabled': addon_user_settings_enabled,
    }, http_status.HTTP_200_OK


@must_be_logged_in
def datasteward_user_config_post(auth, **kwargs):
    """View for post DataSteward user settings with enabled value"""
    data = request.get_json()
    enabled = data.get('enabled', None)
    if enabled is None or not isinstance(enabled, bool):
        # If request's 'enabled' field is not valid, return HTTP 400
        return {}, http_status.HTTP_400_BAD_REQUEST

    user = auth.user
    # If user is not a DataSteward when enabling DataSteward add-on, return HTTP 403
    if not user.is_data_steward and enabled:
        return {}, http_status.HTTP_403_FORBIDDEN

    # Update add-on user settings
    addon_user_settings = user.get_addon(SHORT_NAME)
    addon_user_settings.enabled = enabled
    addon_user_settings.save()

    if enabled:
        # Enable DataSteward addon process
        enable_result = enable_datasteward_addon(auth)

        if not enable_result:
            return {}, http_status.HTTP_500_INTERNAL_SERVER_ERROR

        return {}, http_status.HTTP_200_OK
    else:
        # Disable DataSteward addon process
        skipped_projects = disable_datasteward_addon(auth)

        if skipped_projects is None:
            return {}, http_status.HTTP_500_INTERNAL_SERVER_ERROR

        response_body = {
            'skipped_projects': [
                {
                    'guid': project._id,
                    'name': project.title
                }
                for project in skipped_projects
            ]
        }

        return response_body, http_status.HTTP_200_OK


def enable_datasteward_addon(auth, is_authenticating=False, **kwargs):
    """Start enable DataSteward add-on process"""
    # Check if user has any affiliated institutions
    affiliated_institutions = auth.user.affiliated_institutions.all()
    if not affiliated_institutions:
        return False

    # Start enabling DataSteward add-on process
    with transaction.atomic():
        for institution in affiliated_institutions:
            # Get projects from institution
            projects = institution.nodes.filter(type=OSF_NODE, is_deleted=False)
            for project in projects:
                set_project_permission_to_admin(project=project, auth=auth, is_authenticating=is_authenticating)
    return True


def set_project_permission_to_admin(project, auth, is_authenticating):
    """Force add or set project permission to administrator"""
    user = auth.user
    try:
        if not project.is_contributor(user):
            # If user is not project's contributor, add user to contributor list
            add_result = project.add_contributor(user, permissions=ADMIN, visible=True, send_email=None, auth=auth, log=True, save=True)
            if add_result:
                contributor = project.contributor_class.objects.get(user=user, node=project)
                contributor.is_data_steward = True
                contributor.save()
        else:
            # Get contributor by user's id and project's id
            contributor = project.contributor_class.objects.get(user=user, node=project)
            if not contributor.is_data_steward:
                # If contributor's current permission is not set by DataSteward add-on
                # set is_data_steward to True and data_steward_old_permission to contributor's current permission
                contributor.data_steward_old_permission = contributor.permission
                contributor.is_data_steward = True
                contributor.save()

            if contributor.permission != ADMIN:
                # If contributor's permission is not Project Administrator, update user's permission to Project Administrator
                project.update_contributor(user, permission=ADMIN, visible=True, auth=auth, save=True, check_admin_permission=False)
    except Exception as e:
        # If error is raised while running on "Configure add-on accounts" screen, raise error
        # Otherwise, do nothing
        logger.error('Project {}: error raised while enabling DataSteward add-on with message "{}"'.format(project._id, e))
        if not is_authenticating:
            raise e


def disable_datasteward_addon(auth, **kwargs):
    """Start disable DataSteward add-on process"""
    # Check if user has any affiliated institutions
    affiliated_institutions = auth.user.affiliated_institutions.all()
    if not affiliated_institutions:
        return None

    # Start disabling DataSteward add-on process
    skipped_projects = []
    for institution in affiliated_institutions:
        # Get projects from institution
        projects = institution.nodes.filter(type=OSF_NODE, is_deleted=False)
        for project in projects:
            revert_project_permission(project=project, auth=auth, skipped_projects=skipped_projects)
    return skipped_projects


def revert_project_permission(project, auth, skipped_projects):
    """Force restore old project permission or remove from project"""
    user = auth.user
    try:
        # If user is not contributor of project, skip this project
        if not project.is_contributor(user):
            return

        # Get contributor by user's id and project's id
        contributor = project.contributor_class.objects.get(user=user, node=project)

        # If user is not data steward of project, skip this project
        if not contributor.is_data_steward:
            return

        if contributor.data_steward_old_permission is not None:
            # If user had contributor's old permission before enabling add-on in project, restore that permission
            project.update_contributor(user, permission=contributor.data_steward_old_permission, visible=None,
                                       auth=auth, save=True, check_admin_permission=False)
            contributor.is_data_steward = False
            contributor.data_steward_old_permission = None
            contributor.save()
        else:
            # Otherwise, remove contributor from project
            remove_result = project.remove_contributor(user, auth=auth, log=True)
            if not remove_result:
                # If user is not remove from project, log warning and add project to skipped project list
                logger.warning('Cannot remove user from project {}'.format(project._id))
                skipped_projects.append(project)
    except Exception as e:
        # If error is raised, log warning and add project to skipped project list
        logger.warning('Project {}: error raised while disabling DataSteward add-on with message "{}"'.format(project._id, e))
        skipped_projects.append(project)
