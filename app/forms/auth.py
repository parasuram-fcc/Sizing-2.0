from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    email = StringField("Email-ID", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField("Log In")


class RegisterForm(FlaskForm):
    # email is pre-filled and readonly after OTP verification
    email = StringField("Email-ID", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    name = StringField("Your Name", validators=[DataRequired(), Length(max=100)])
    initial = StringField("Initial", validators=[DataRequired(), Length(max=4)])
    # NOTE: route sets employeeId=None for all new users, so this field is optional
    employeeId = StringField("Employee ID", validators=[Optional()])
    # mobile was PasswordField (bug) — corrected to StringField; no auth logic change
    mobile = StringField("Mobile", validators=[DataRequired(), Length(max=20)])
    # department and designation are rendered as <select> in the template
    department = StringField("Department", validators=[DataRequired()])
    designation = StringField("Designation", validators=[DataRequired()])
    submit = SubmitField("Register")


class EmailOTPForm(FlaskForm):
    email = StringField("Email-ID", validators=[DataRequired(), Email()])
    otp = StringField("OTP", validators=[DataRequired()])
    submit = SubmitField("Verify OTP")


class ResetPasswordRequestForm(FlaskForm):
    email = StringField("Email-ID", validators=[DataRequired(), Email()])
    submit = SubmitField("Send OTP")


class ResetPasswordForm(FlaskForm):
    otp = StringField("OTP", validators=[DataRequired()])
    password = PasswordField("New Password", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField("Reset Password")
