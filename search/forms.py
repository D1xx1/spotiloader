from django import forms

class SearchForm(forms.Form):
    q = forms.CharField(
        label="Поиск трека в Spotify (название или ссылка)",
        max_length=300,
        widget=forms.TextInput(attrs={
            "placeholder": "Название или ссылку на трек в Spotify",
            "class": "input"
        }),
    )
