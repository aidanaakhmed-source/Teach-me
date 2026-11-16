from django.conf import settings
from django.db import DatabaseError, transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .demo import DEMO_TITLE, DEMO_TEXT
from .forms import FlashcardForm, SourceForm
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

    all_cards = source.cards.all()

    total_count = all_cards.count()
    verified_count = all_cards.filter(is_verified=True).count()
    pending_count = total_count - verified_count

    status = request.GET.get('status', 'all')
    if status not in ('all', 'pending', 'verified'):
        status = 'all'

    if status == 'pending':
        cards = all_cards.filter(is_verified=False)
    elif status == 'verified':
        cards = all_cards.filter(is_verified=True)
    else:
        cards = all_cards

    return render(
        request,
        'study/source_detail.html',
        {
            'source': source,
            'cards': cards,
            'status': status,
            'total_count': total_count,
            'verified_count': verified_count,
            'pending_count': pending_count,
        }
    )


def card_edit(request, pk):
    card = get_object_or_404(Flashcard, pk=pk)

    if request.method == 'POST':
        form = FlashcardForm(request.POST, instance=card)

        if form.is_valid():
            updated = form.save(commit=False)
            updated.is_verified = False
            updated.save()
            return redirect('source_detail', pk=card.source_id)
    else:
        form = FlashcardForm(instance=card)

    return render(
        request,
        'study/card_form.html',
        {
            'form': form,
            'card': card,
        }
    )


def card_delete(request, pk):
    card = get_object_or_404(Flashcard, pk=pk)

    if request.method == 'POST':
        source_id = card.source_id
        card.delete()
        return redirect('source_detail', pk=source_id)

    return render(
        request,
        'study/card_confirm_delete.html',
        {
            'card': card,
        }
    )


@require_POST
def card_review(request, pk):
    card = get_object_or_404(Flashcard, pk=pk)
    action = request.POST.get('action')

    if action == 'verify':
        card.is_verified = True
        card.save(update_fields=['is_verified'])
    elif action == 'reset':
        card.is_verified = False
        card.save(update_fields=['is_verified'])
    else:
        return HttpResponseBadRequest('Белгісіз әрекет.')

    return redirect('source_detail', pk=card.source_id)