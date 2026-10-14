"""Safe domain error codes without sensitive values."""


class ProfileError(Exception):
    code = "profile_error"
    status = 400


class ProfileNotFound(ProfileError):
    code = "profile_not_found"
    status = 404


class ProfileExists(ProfileError):
    code = "profile_already_exists"
    status = 409


class PhoneTaken(ProfileError):
    code = "phone_unavailable"
    status = 409
