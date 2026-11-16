from django.conf import settings
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from .demo import DEMO_TITLE, DEMO_TEXT
from .forms import SourceForm
from .models import Flashcard, Source
from .services import generate_cards, GenerationError


def home(request):
    mode = getattr(settings, "TEACHME_MODE", "demo")

    try:
        sources = list(Source.objects.all())
    except DatabaseError:
        sources = []

    if request.method == 'POST':
        form = SourceForm(request.POST)

        if form.is_valid():
            text = form.cleaned_data['text']

            try:
                cards = generate_cards(text)
            except GenerationError as error:
                form.add_error(None, str(error))
            else:
                try:
                    with transaction.atomic():
                        source = Source.objects.create(
                            title=form.cleaned_data['title'],
                            text=text,
                            generation_mode=mode,
                        )
                        for position, card in enumerate(cards, 1):
                            Flashcard.objects.create(
                                source=source,
                                position=position,
                                question=card['question'],
                                answer=card['answer'],
                                source_quote=card['source_quote'],
                            )
                except DatabaseError:
                    form.add_error(
                        None,
                        'Дерекқорға сақтау кезінде қате орын алды. Қайта көріңіз.',
                    )
                else:
                    return redirect('source_detail', pk=source.pk)
    else:
        form = SourceForm(
            initial={
                'title': DEMO_TITLE,
                'text': DEMO_TEXT,
            }
        )

    return render(
        request,
        'study/home.html',
        {
            'form': form,
            'mode': mode,
            'sources': sources,
        }
    )


def source_detail(request, pk):
    source = get_object_or_404(Source, pk=pk)
    cards = source.cards.all()

    return render(
        request,
        'study/source_detail.html',
        {
            'source': source,
            'cards': cards,
        }
    )