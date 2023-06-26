
import os

class InfraUtilInterface():
    
    def get_screen_status(self):
        pass

    def get_screen_lock_time(self):
        pass

    def get_screen_unlock_time(self):
        pass

class InfraFactory():
    
    def get_infra_util(infra_type=None):
        if infra_type == "mac":
            return MacOsInfraUtil()


class MacOsInfraUtil(InfraUtilInterface):

    def get_screen_status(self):
        pass

    def get_screen_lock_time(self):
        pass

    def get_screen_unlock_time(self):
        pass


