from django.utils.translation import LANGUAGE_SESSION_KEY

class SetLanguage(object):
    def setUserLanguage(self,request,exception):
        request.session[LANGUAGE_SESSION_KEY] = "pt-pt"
        return "Hello"