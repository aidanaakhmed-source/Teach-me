from django.test import TestCase
from django.urls import reverse

from .demo import DEMO_TEXT, DEMO_TITLE
from .models import Source


class DemoTests(TestCase):
    """№8 DEMO: генерация мен көрсету негізгі тексерулері."""

    def _count_card_summaries(self, response):
        # Конспект блогы <details>/<summary> қолданбайды.
        # Карточка жауабы әр карточканың <summary> ішінде.
        # Тілге тәуелсіз болу үшін ашылатын <summary> тегін санаймыз —
        # бұл карточка санына дәл тең.
        return response.content.decode().count('<summary>')

    def test_home_get_renders_demo_prefill(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, DEMO_TITLE)
        self.assertContains(response, DEMO_TEXT)

    def test_home_post_creates_source_and_cards(self):
        response = self.client.post(
            reverse('home'),
            {'title': 'Демо конспект', 'text': DEMO_TEXT},
        )
        self.assertEqual(response.status_code, 302)
        source = Source.objects.get(title='Демо конспект')
        self.assertRedirects(response, reverse('source_detail', pk=source.pk))
        self.assertEqual(source.generation_mode, 'demo')
        self.assertGreater(source.cards.count(), 0)

    def test_source_detail_shows_conspectus_and_cards(self):
        self.client.post(
            reverse('home'),
            {'title': 'Демо конспект', 'text': DEMO_TEXT},
        )
        source = Source.objects.get(title='Демо конспект')
        response = self.client.get(reverse('source_detail', pk=source.pk))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Конспект')
        self.assertEqual(
            self._count_card_summaries(response),
            source.cards.count(),
        )