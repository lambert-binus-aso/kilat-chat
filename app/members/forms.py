from django import forms

from .models import User

from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password


class SignupForm(forms.ModelForm):
    email = forms.EmailField(max_length=128)
    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8,
        max_length=128,
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if not username:
            raise forms.ValidationError('Enter a username.')
        return username

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password = make_password(self.cleaned_data['password'])

        if commit:
            user.save()
        return user

class LoginForm(forms.Form):

    email = forms.EmailField(max_length=128)
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if not email or not password:
            return cleaned_data

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise forms.ValidationError("Invalid email or password")

        if not check_password(password, user.password):
            raise forms.ValidationError("Invalid email or password")

        self.user = user

        return cleaned_data
