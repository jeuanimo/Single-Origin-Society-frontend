from django import forms
from accounts.models import User


class InquiryFilterForm(forms.Form):
    q = forms.CharField(required=False)
    from_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    to_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    platform = forms.CharField(required=False)


class InquiryAssignForm(forms.Form):
    assigned_to = forms.ModelChoiceField(queryset=User.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(is_staff=True).order_by("first_name", "last_name", "username")


class InquiryNoteForm(forms.Form):
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 4, "class": "p-form-control"}), max_length=2000)
