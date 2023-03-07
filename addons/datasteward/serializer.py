from addons.base.serializer import AddonSerializer


class DataStewardSerializer(AddonSerializer):
    addon_short_name = 'datasteward'

    REQUIRED_URLS = []

    def addon_serialized_urls(self):
        pass

    def serialized_urls(self):
        pass

    def user_is_owner(self):
        pass

    def credentials_owner(self):
        pass
