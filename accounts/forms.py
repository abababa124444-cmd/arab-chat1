from django import forms


class SignupForm(forms.Form):
    name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=20)


class VerifyForm(forms.Form):
    phone = forms.CharField(widget=forms.HiddenInput())
    name = forms.CharField(max_length=100, required=False, widget=forms.HiddenInput())
    code = forms.CharField(max_length=6)
