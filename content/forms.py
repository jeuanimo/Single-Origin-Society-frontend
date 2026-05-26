from django import forms

from .models import AmbassadorInquiry, WholesaleInquiry


class WholesaleInquiryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} form-control".strip()

    class Meta:
        model = WholesaleInquiry
        fields = [
            "name",
            "email",
            "company_name",
            "website",
            "phone",
            "location",
            "monthly_volume",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class AmbassadorInquiryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} form-control".strip()

    class Meta:
        model = AmbassadorInquiry
        fields = [
            "name",
            "email",
            "social_handle",
            "primary_platform",
            "audience_size",
            "city",
            "pitch",
        ]
        widgets = {
            "pitch": forms.Textarea(attrs={"rows": 5}),
        }
