from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Room, Message, DirectThread, DirectMessage
import socket


def home(request: HttpRequest) -> HttpResponse:
    return render(request, 'core/home.html')


@require_http_methods(["GET", "POST"])
def room_list(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        if name:
            room, _ = Room.objects.get_or_create(name=name)
            if not room.slug:
                room.save()
            return redirect('core:room_detail', slug=room.slug)
    rooms = Room.objects.order_by('-created_at')
    return render(request, 'core/room_list.html', {'rooms': rooms})


@require_http_methods(["GET", "POST"])
def room_detail(request: HttpRequest, slug: str) -> HttpResponse:
    room = get_object_or_404(Room, slug=slug)
    if request.method == 'POST':
        author_name = (request.POST.get('author_name') or 'مجهول').strip() or 'مجهول'
        content = (request.POST.get('content') or '').strip()
        if content:
            Message.objects.create(room=room, author_name=author_name, content=content)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': True})
            return redirect('core:room_detail', slug=room.slug)
    messages = room.messages.all()[:200]
    rooms = Room.objects.order_by('-created_at')[:50]
    return render(request, 'core/room_detail.html', {'room': room, 'messages': messages, 'rooms': rooms})


def api_messages(request: HttpRequest, slug: str) -> JsonResponse:
    room = get_object_or_404(Room, slug=slug)
    after_id = int(request.GET.get('after', 0))
    qs = room.messages.filter(id__gt=after_id).values('id', 'author_name', 'content', 'created_at')
    data = [
        {
            'id': m['id'],
            'author_name': m['author_name'],
            'content': m['content'],
            'created_at': m['created_at'].isoformat(),
        }
        for m in qs
    ]
    return JsonResponse({'messages': data})


def _lan_ips() -> list[str]:
    ips = set()
    try:
        # Method 1: hostname resolution
        hostname = socket.gethostname()
        _, _, addrs = socket.gethostbyname_ex(hostname)
        for a in addrs:
            if '.' in a:
                ips.add(a)
    except Exception:
        pass
    try:
        # Method 2: UDP connect trick (no traffic sent)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    ips.update({'127.0.0.1'})
    return sorted(ips)


def connect(request: HttpRequest) -> HttpResponse:
    port = request.get_port() or '8000'
    candidates = [f"http://{ip}:{port}" for ip in _lan_ips()]
    # choose a non-loopback if available
    primary = next((u for u in candidates if not u.startswith('http://127.')), candidates[0])
    return render(request, 'core/connect.html', {
        'primary_url': primary,
        'candidate_urls': candidates,
    })


@login_required
def dm_list(request: HttpRequest) -> HttpResponse:
    me = request.user
    threads = DirectThread.objects.filter(Q(user1=me) | Q(user2=me)).order_by('-created_at')
    return render(request, 'core/dm_list.html', {'threads': threads})


@login_required
@require_http_methods(["GET", "POST"])
def dm_thread(request: HttpRequest, user_id: int) -> HttpResponse:
    me = request.user
    other = get_object_or_404(User, id=user_id)
    if me.id == other.id:
        return redirect('core:dm_list')
    # get or create deterministic order
    u1, u2 = (me, other) if me.id <= other.id else (other, me)
    thread, _ = DirectThread.objects.get_or_create(user1=u1, user2=u2)
    if request.method == 'POST':
        content = (request.POST.get('content') or '').strip()
        if content:
            DirectMessage.objects.create(thread=thread, author=me, content=content)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': True})
            return redirect('core:dm_thread', user_id=other.id)
    msgs = thread.messages.select_related('author').all()[:500]
    return render(request, 'core/dm_thread.html', {'thread': thread, 'other': other, 'messages': msgs})
