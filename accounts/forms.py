import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Email, Length, ValidationError, Regexp
from config import User
from flask_wtf.recaptcha import RecaptchaField


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(message="Please enter a valid email address.")])
    firstname = StringField('First Name',
                            validators=[
                                DataRequired(),
                                Length(min=3, max=12, message="3 to 15 character."),
                                Regexp(re.compile(r"^[A-Za-z-]+$"), message="Please enter letters or hyphens only")])

    lastname = StringField('Last Name',
                           validators=[
                               DataRequired(),
                               Length(min=3, max=12, message="3 and 10 characters"),
                               Regexp(re.compile(r"^[A-Za-z-]+$"), message="Please enter letters or hyphens only")])

    phone = StringField('Phone',
                        validators=[
                            DataRequired(),
                            Length(max=15, message="Phone number up to 15 characters."),
                            Regexp(
                                re.compile(r"\A02\d-\d{8}\Z|"
                                           r"\A011\d-\d{7}\Z|"
                                           r"\A01\d1-\d{7}\Z|"
                                           r"\A01\d{3}-\d{5,6}\Z"),
                                message="Only UK landline phone number format is allowed")])

    password = PasswordField('Password', validators=[DataRequired()])

    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password',
                                                                                             message='Both password fields must be equal!')])

    submit = SubmitField('Register')

    def validate_lastname(self, field):
        name = User.query.filter_by(lastname=field.data).first()
        if name is not None:
            raise ValidationError('Username already taken.')

    def validate_password(self, password):
        password = password.data
        minimal_length = 8
        maximum_length = 15

        uppercase_regex = re.compile(r'[A-Z]')
        lowercase_regex = re.compile(r'[a-z]')
        digits_regex = re.compile(r'[0-9]')
        special_char_regex = re.compile(r'[!@#$%^&*()_+\-={}:?~\\/,.|<>]')

        if not special_char_regex.search(password):
            print("Missing special character")
            raise ValidationError("Password should contain at least one special character")
        if len(password) < minimal_length or len(password) > maximum_length:
            raise ValidationError(f"Password must be between {minimal_length} and {maximum_length} characters.")

        if not uppercase_regex.search(password) or not lowercase_regex.search(password):
            raise ValidationError("Password should contain at least one uppercase letter and one lowercase letter.")

        if not digits_regex.search(password):
            raise ValidationError("Password should contain at least one digit")

        return "Strong Password is valid"


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    mfa_code = StringField('MFA Code')
    submit = SubmitField('Log In')
    recaptcha = RecaptchaField()

    # validate whether mfa code entered or not, provide hint message
    def validate_is_enter_mfa_code(self, mfa_code):
        if mfa_code.data and self.submit.data:
            return True
        else:
            raise ValidationError("MFA Code can not be empty")
