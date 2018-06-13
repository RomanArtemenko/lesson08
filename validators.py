from abc import ABCMeta, abstractmethod

class BaseValidator(metaclass=ABCMeta):
    
    def __init__(self):
        self._errors = {}

    @property    
    def errors(self):
        return self._errors

    def _set_error(self, key, msg):
        if not key in self._errors.keys():
            self.errors[key] = []
        self._errors[key].append(msg)

    @abstractmethod
    def validate(self):
        pass
    

class UserValidator(BaseValidator):
    
    def __init__(self, data, redis):
        super().__init__()
        self._username = data["username"]
        self._password = data["password"]
        self._confirm_password = data["confirm_password"]
        self._redis = redis
    
    def _username_is_empty(self):
        if not self._username:
            self._set_error("username","Username is required")

    def _username_len(self):
        if len(self._username) > 20:
            self._set_error("username","Username is too long")                

    def _password_is_empty(self):
        if not self._password:
            self._set_error("password","Password is required")

    def _password_len(self):
        if len(self._password) > 20:
            self._set_error("password","Password is too long")      

    def _confirm_password_is_empty(self):
        if not self._password:
            self._set_error("confirm_password","Confirm_assword is required")

    def _confirm_password_len(self):
        if len(self._confirm_password) > 20:
            self._set_error("confirm_password","Confirm_password is too long")      

    def _password_equals_confirm_password(self):
        if not self._password == self._confirm_password:
            self._set_error("password", "Password and confirm_password must be equals")

    def _user_exist(self):
        if self._redis.exists(self._username):
            self._set_error("username","User with this name already exists")               

    def validate(self):
        self._username_is_empty()
        self._password_is_empty()
        self._confirm_password_is_empty()
        self._username_len()
        self._password_len()
        self._confirm_password_len()
        self._user_exist()
        self._password_equals_confirm_password()        

class AdvertValidator(BaseValidator):
    
    def __init__(self, data):
        super().__init__()
        self._advert = data["text"]

    def _advert_len(self):
        if len(self._advert) > 50:
            self._set_error("advert","Advert is too long")

    def validate(self):
        self._advert_len()
        

class CommentValidator(BaseValidator):
    
    def __init__(self, data):
        super().__init__()
        self._comment = data["text"]

    def _advert_len(self):
        if len(self._comment) > 255:
            self._set_error("comment","Comment is too long")

    def validate(self):
        self._advert_len()
