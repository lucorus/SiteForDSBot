from django import forms
from django.contrib.auth.forms import AuthenticationForm


class UserLoginForm(AuthenticationForm):
    password1 = forms.TextInput,
    password2 = forms.TextInput,

    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'введите ваш никнейм'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': "введите пароль"})