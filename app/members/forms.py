from django import forms

from .models import User


class SignupForm(forms.ModelForm):
    email = forms.EmailField(max_length=128)

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if not username:
            raise forms.ValidationError('Enter a username.')
        return username
