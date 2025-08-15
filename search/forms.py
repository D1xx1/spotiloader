from django import forms

class SearchForm(forms.Form):
    q = forms.CharField(
        label="Поиск трека в Spotify (название или ссылка)",
        max_length=300,
        widget=forms.TextInput(attrs={
            "placeholder": "Например: Linkin Park - Numb ИЛИ https://open.spotify.com/track/…",
            "class": "input"
        }),
    )
