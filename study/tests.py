import copy
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

from .demo import DEMO_CARDS, DEMO_TEXT
from .models import Flashcard, Source
from .services import GenerationError, validate_cards


class HomeViewTests(TestCase):

    def test_valid_demo_post_creates_source_and_cards(self):
        response = self.client.post(
            reverse('home'),
            {'title': 'Тест тақырыбы', 'text': DEMO_TEXT},
        )
        source = Source.objects.get()
        self.assertRedirects(
            response,
            reverse('source_detail', kwargs={'pk': source.pk}),
        )
        self.assertEqual(Source.objects.count(), 1)
        self.assertEqual(Flashcard.objects.count(), 3)

    @patch('study.views.generate_cards')
    def test_short_text_does_not_call_provider(self, mock_generate):
        response = self.client.post(
            reverse('home'),
            {'title': 'Тест', 'text': 'short'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(mock_generate.called)
        self.assertFalse(Source.objects.exists())
        self.assertTrue(response.context['form'].errors)

    def test_bad_quote_rejects_whole_payload(self):
        payload = copy.deepcopy({'cards': DEMO_CARDS})
        for card in payload['cards']:
            card['source_quote'] = 'Этого нет в исходном тексте.'
        with self.assertRaises(GenerationError):
            validate_cards(payload, DEMO_TEXT)

    @patch('study.views.generate_cards')
    def test_provider_generation_error_returns_bound_form(self, mock_generate):
        mock_generate.side_effect = GenerationError('Тест қатесі')
        response = self.client.post(
            reverse('home'),
            {'title': 'Тест', 'text': DEMO_TEXT},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Source.objects.exists())
        self.assertFalse(Flashcard.objects.exists())
        self.assertTrue(response.context['form'].errors)

    def test_database_error_on_second_card_rolls_back_everything(self):
        original_save = Flashcard.save
        state = {'save_count': 0}

        def fake_save(instance, *args, **kwargs):
            state['save_count'] += 1
            if state['save_count'] == 2:
                raise DatabaseError('simulated')
            return original_save(instance, *args, **kwargs)

        with patch.object(Flashcard, 'save', fake_save):
            response = self.client.post(
                reverse('home'),
                {'title': 'Тест', 'text': DEMO_TEXT},
            )

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(state['save_count'], 2)
        self.assertFalse(Source.objects.exists())
        self.assertFalse(Flashcard.objects.exists())
        self.assertTrue(response.context['form'].errors)

    @patch('study.views.generate_cards')
    def test_detail_view_does_not_call_provider(self, mock_generate):
        source = Source.objects.create(
            title='Тест',
            text=DEMO_TEXT,
            generation_mode='demo',
        )
        for position in range(1, 4):
            Flashcard.objects.create(
                source=source,
                position=position,
                question=f'Q{position}',
                answer=f'A{position}',
                source_quote='IP-адрес',
            )

        sources_before = Source.objects.count()
        cards_before = Flashcard.objects.count()

        first = self.client.get(
            reverse('source_detail', kwargs={'pk': source.pk}),
        )
        second = self.client.get(
            reverse('source_detail', kwargs={'pk': source.pk}),
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(mock_generate.called)
        self.assertEqual(Source.objects.count(), sources_before)
        self.assertEqual(Flashcard.objects.count(), cards_before)