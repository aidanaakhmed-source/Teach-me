from django import forms

from .models import Flashcard


class SourceForm(forms.Form):
    title = forms.CharField(
        max_length=120,
        required=True,
        strip=True
    )

    text = forms.CharField(
        min_length=80,
        max_length=12000,
        required=True,
        strip=True,
        widget=forms.Textarea
    )

    def clean_text(self):
        text = self.cleaned_data['text']
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text


class FlashcardForm(forms.ModelForm):
    class Meta:
        model = Flashcard
        fields = ['question', 'answer', 'source_quote']
        labels = {
            'question': 'Сұрақ',
            'answer': 'Жауап',
            'source_quote': 'Дәйексөз',
        }

    def clean_source_quote(self):
        quote = self.cleaned_data.get('source_quote', '')
        quote = quote.replace('\r\n', '\n').replace('\r', '\n')

        source_text = self.instance.source.text or ''
        source_text = source_text.replace('\r\n', '\n').replace('\r', '\n')

        if quote not in source_text:
            raise forms.ValidationError(
                'Дәйексөз конспект мәтінінде дәл кездеспейді. '
                'Конспект мәтінінен сөзбе-сөз көшіріңіз.'
            )
        return quote