from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse

from .forms import SignupForm, VerifyForm
from .models import Profile, OTP, Friendship
from .services import normalize_phone, create_otp, send_whatsapp_otp_via_twilio


@csrf_exempt
@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect('core:room_list')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name'].strip()
            phone = normalize_phone(form.cleaned_data['phone'])
            # Persist pending data in session as fallback
            request.session['pending_phone'] = phone
            request.session['pending_name'] = name
            otp, created = create_otp(phone, OTP.PURPOSE_SIGNUP)
            send_whatsapp_otp_via_twilio(phone, otp.code)
            verify_form = VerifyForm(initial={'phone': phone, 'name': name})
            return render(request, 'accounts/verify.html', {'form': verify_form, 'phone': phone, 'name': name})
    else:
        form = SignupForm()
    return render(request, 'accounts/signup.html', {'form': form})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def verify(request):
    if request.user.is_authenticated:
        return redirect('core:room_list')
    if request.method == 'POST':
        form = VerifyForm(request.POST)
        if form.is_valid():
            # Pull from form or session fallback
            phone_val = form.cleaned_data.get('phone') or request.session.get('pending_phone')
            name_val = form.cleaned_data.get('name') or request.session.get('pending_name')
            phone = normalize_phone(phone_val or '')
            name = (name_val or 'مستخدم').strip() or 'مستخدم'
            code = form.cleaned_data['code'].strip()
            otp = OTP.objects.filter(phone=phone, is_used=False).order_by('-created_at').first()
            if not otp:
                messages.error(request, 'لم يتم العثور على رمز صالح. الرجاء إعادة الإرسال من صفحة التسجيل.')
                return redirect('accounts:signup')
            if otp.is_expired():
                messages.error(request, 'انتهت صلاحية الرمز. الرجاء المحاولة مجدداً.')
                return redirect('accounts:signup')
            if otp.code != code:
                otp.attempts += 1
                otp.save(update_fields=['attempts'])
                messages.error(request, 'رمز غير صحيح.')
                return render(request, 'accounts/verify.html', {'form': form, 'phone': phone})
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            user = User.objects.filter(profile__phone=phone).first()
            if not user:
                username = f"user_{timezone.now().timestamp()}"
                user = User.objects.create_user(username=username)
                Profile.objects.create(user=user, phone=phone, name=name)
            else:
                # Update missing name if empty
                if not user.profile.name:
                    user.profile.name = name
                    user.profile.save(update_fields=['name'])
            login(request, user)
            # Clear pending session
            request.session.pop('pending_phone', None)
            request.session.pop('pending_name', None)
            return redirect('accounts:contacts_sync')
    else:
        # Prevent direct GET without context
        return redirect('accounts:signup')
    return render(request, 'accounts/verify.html', {'form': form})


@login_required
def dashboard(request):
    return redirect('core:room_list')


def logout_view(request):
    logout(request)
    return redirect('accounts:signup')


@csrf_exempt
@login_required
@require_http_methods(["GET", "POST"])
def contacts_sync(request):
    matches = []
    sample = request.user.profile.phone if hasattr(request.user, 'profile') else ''
    if request.method == 'POST':
        raw = (request.POST.get('numbers') or '').strip()
        nums = []
        for line in raw.splitlines():
            n = normalize_phone(line)
            if n:
                nums.append(n)
        nums = list(dict.fromkeys(nums))  # dedupe preserve order
        if nums:
            # تحديث: إضافة user_id للنتائج حتى يعمل زر الدردشة
            profiles = Profile.objects.filter(phone__in=nums).select_related('user')
            matches = [
                {
                    'name': p.name,
                    'phone': p.phone,
                    'user_id': p.user.id
                }
                for p in profiles
            ]
    return render(request, 'accounts/contacts_sync.html', {
        'matches': matches,
        'sample': sample,
    })


@login_required
def users_list(request):
    """عرض قائمة جميع المستخدمين مع البحث"""
    # استبعاد المستخدم الحالي والمستخدمين بدون profile
    users = User.objects.filter(profile__isnull=False).exclude(id=request.user.id).select_related('profile')
    
    # البحث
    query = request.GET.get('q', '').strip()
    if query:
        users = users.filter(
            Q(profile__name__icontains=query) | 
            Q(profile__phone__icontains=query)
        )
    
    # ترتيب حسب الأحدث
    users = users.order_by('-profile__created_at')
    
    # Pagination
    paginator = Paginator(users, 20)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)
    
    # إضافة حالة الصداقة لكل مستخدم
    for user in users_page:
        user.friendship = Friendship.get_friendship_status(request.user, user)
        user.is_friend = Friendship.are_friends(request.user, user)
        user.is_blocked = Friendship.is_blocked(request.user, user)
    
    return render(request, 'accounts/users_list.html', {
        'users': users_page,
        'query': query,
        'total_count': users.count()
    })


@login_required
def friends_list(request):
    """عرض قائمة الأصدقاء والطلبات المعلقة"""
    # الأصدقاء المقبولين
    friends_sent = Friendship.objects.filter(
        from_user=request.user,
        status=Friendship.STATUS_ACCEPTED
    ).select_related('to_user__profile')
    
    friends_received = Friendship.objects.filter(
        to_user=request.user,
        status=Friendship.STATUS_ACCEPTED
    ).select_related('from_user__profile')
    
    # دمج الأصدقاء
    friends = []
    for f in friends_sent:
        friends.append(f.to_user)
    for f in friends_received:
        friends.append(f.from_user)
    
    # الطلبات المعلقة المرسلة
    pending_sent = Friendship.objects.filter(
        from_user=request.user,
        status=Friendship.STATUS_PENDING
    ).select_related('to_user__profile')
    
    # الطلبات المعلقة المستلمة
    pending_received = Friendship.objects.filter(
        to_user=request.user,
        status=Friendship.STATUS_PENDING
    ).select_related('from_user__profile')
    
    # المحظورين
    blocked = Friendship.objects.filter(
        from_user=request.user,
        status=Friendship.STATUS_BLOCKED
    ).select_related('to_user__profile')
    
    return render(request, 'accounts/friends_list.html', {
        'friends': friends,
        'friends_count': len(friends),
        'pending_sent': pending_sent,
        'pending_received': pending_received,
        'blocked': blocked,
    })


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def send_friend_request(request, user_id):
    """إرسال طلب صداقة"""
    to_user = get_object_or_404(User, id=user_id)
    
    # التحقق من عدم إرسال طلب لنفسك
    if to_user == request.user:
        messages.error(request, 'لا يمكنك إضافة نفسك كصديق')
        return redirect('accounts:users_list')
    
    # التحقق من عدم وجود علاقة سابقة
    existing = Friendship.objects.filter(
        Q(from_user=request.user, to_user=to_user) |
        Q(from_user=to_user, to_user=request.user)
    ).first()
    
    if existing:
        if existing.status == Friendship.STATUS_BLOCKED:
            messages.error(request, 'لا يمكن إرسال طلب صداقة لهذا المستخدم')
        elif existing.status == Friendship.STATUS_ACCEPTED:
            messages.info(request, 'أنتما أصدقاء بالفعل')
        else:
            messages.info(request, 'تم إرسال طلب الصداقة مسبقاً')
    else:
        Friendship.objects.create(
            from_user=request.user,
            to_user=to_user,
            status=Friendship.STATUS_PENDING
        )
        messages.success(request, f'تم إرسال طلب صداقة إلى {to_user.profile.name}')
    
    # العودة للصفحة السابقة أو قائمة المستخدمين
    return redirect(request.META.get('HTTP_REFERER', 'accounts:users_list'))


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def accept_friend_request(request, friendship_id):
    """قبول طلب صداقة"""
    friendship = get_object_or_404(
        Friendship,
        id=friendship_id,
        to_user=request.user,
        status=Friendship.STATUS_PENDING
    )
    
    friendship.status = Friendship.STATUS_ACCEPTED
    friendship.save()
    
    messages.success(request, f'تم قبول طلب صداقة {friendship.from_user.profile.name}')
    return redirect('accounts:friends_list')


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def reject_friend_request(request, friendship_id):
    """رفض طلب صداقة"""
    friendship = get_object_or_404(
        Friendship,
        id=friendship_id,
        to_user=request.user,
        status=Friendship.STATUS_PENDING
    )
    
    friendship.delete()
    messages.success(request, 'تم رفض طلب الصداقة')
    return redirect('accounts:friends_list')


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def cancel_friend_request(request, friendship_id):
    """إلغاء طلب صداقة تم إرساله"""
    friendship = get_object_or_404(
        Friendship,
        id=friendship_id,
        from_user=request.user,
        status=Friendship.STATUS_PENDING
    )
    
    friendship.delete()
    messages.success(request, 'تم إلغاء طلب الصداقة')
    return redirect(request.META.get('HTTP_REFERER', 'accounts:friends_list'))


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def remove_friend(request, user_id):
    """إزالة صديق"""
    other_user = get_object_or_404(User, id=user_id)
    
    friendship = Friendship.objects.filter(
        Q(from_user=request.user, to_user=other_user) |
        Q(from_user=other_user, to_user=request.user),
        status=Friendship.STATUS_ACCEPTED
    ).first()
    
    if friendship:
        friendship.delete()
        messages.success(request, f'تم إزالة {other_user.profile.name} من الأصدقاء')
    
    return redirect(request.META.get('HTTP_REFERER', 'accounts:friends_list'))


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def block_user(request, user_id):
    """حظر مستخدم"""
    to_user = get_object_or_404(User, id=user_id)
    
    if to_user == request.user:
        messages.error(request, 'لا يمكنك حظر نفسك')
        return redirect('accounts:users_list')
    
    # حذف أي علاقة سابقة
    Friendship.objects.filter(
        Q(from_user=request.user, to_user=to_user) |
        Q(from_user=to_user, to_user=request.user)
    ).delete()
    
    # إنشاء علاقة حظر
    Friendship.objects.create(
        from_user=request.user,
        to_user=to_user,
        status=Friendship.STATUS_BLOCKED
    )
    
    messages.success(request, f'تم حظر {to_user.profile.name}')
    return redirect(request.META.get('HTTP_REFERER', 'accounts:users_list'))


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def unblock_user(request, user_id):
    """إلغاء حظر مستخدم"""
    to_user = get_object_or_404(User, id=user_id)
    
    Friendship.objects.filter(
        from_user=request.user,
        to_user=to_user,
        status=Friendship.STATUS_BLOCKED
    ).delete()
    
    messages.success(request, f'تم إلغاء حظر {to_user.profile.name}')
    return redirect('accounts:friends_list')
