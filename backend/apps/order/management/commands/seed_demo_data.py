"""
生成演示环境的一批『非空展示数据』（幂等）

用途：让后台/前台演示时各模块都有可看的数据，而不是空壳。

覆盖：
  1) 演示用户（demo01…demoNN）
  2) 订单 + 订单项（约 320 单，覆盖各种状态与支付/物流节点）
  3) 商品评价（Review）
  4) 收藏（Favorite）
  5) 购物车（Cart + CartItem）
  6) 优惠券（Coupon）与用户优惠券（UserCoupon）
  7) 浏览历史（BrowseHistory）
  8) 收货地址（Address，若有该模块）

幂等：不重复创建同名用户；订单按唯一订单号去重；其它模块按唯一约束
      get_or_create 风格去重。已存在的演示数据不会被删除或覆盖。

直接写原始行，不调用 pay/ship/complete 等业务方法，避免触发支付/物流/库存
等运行时副作用。

用法：
    python manage.py seed_demo_data                # 全量生成（8 用户 / 320 订单）
    python manage.py seed_demo_data --users=5 --orders=120
    python manage.py seed_demo_data --dry-run
"""
import random
from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from django.core.management.base import BaseCommand

from apps.goods.models import SPU, SKU

from apps.order.models import Order, OrderItem, PaymentStatus


class Command(BaseCommand):
    help = '生成演示数据：订单/订单项、评价、收藏、购物车、优惠券、浏览历史等'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=8, help='演示用户数量')
        parser.add_argument('--orders', type=int, default=320, help='订单数量')
        parser.add_argument('--dry-run', action='store_true', help='只打印计划')
        parser.add_argument('--force', action='store_true', help='即使已有演示订单也强制重新生成')

    def _already_seeded(self):
        """已有 demo 用户的订单即认为此前已播种（避免多次启动重复积压）。"""
        from apps.order.models import Order
        return Order.objects.filter(user__username__startswith='demo').exists()

    def handle(self, *args, **options):
        self.n_users = options['users']
        self.n_orders = options['orders']
        self.dry = options['dry_run']
        self.rng = random.Random(20260916)

        self.spus = list(SPU.objects.filter(deleted_at__isnull=True, status='on_sale'))
        if not self.spus:
            self.stdout.write(self.style.ERROR('没有可用商品（on_sale）'))
            return
        self.users = self._ensure_users()

        self.force = options['force']

        if self.dry:
            self.stdout.write(self.style.SUCCESS(
                f'[DRY] 计划：{len(self.users)} 用户, {self.n_orders} 订单, 商品 {len(self.spus)}, '
                f'SKU {SKU.objects.count()}'))
            return

        if self._already_seeded() and not self.force:
            self.stdout.write(self.style.WARNING(
                '检测到已有演示订单，跳过（幂等）；如需重生成请加 --force'))
            return

        with transaction.atomic():
            created = {}
            created['orders'] = self._seed_orders()
            created['reviews'] = self._seed_reviews()
            created['favorites'] = self._seed_favorites()
            created['carts'] = self._seed_carts()
            created['coupon'] = self._seed_coupons()
            created['browse'] = self._seed_browse_history()
            created['logistics'] = self._seed_logistics()
            created['support'] = self._seed_support()

        self.stdout.write(self.style.SUCCESS(
            f'演示数据完成：{created}'))

    # ---------- 工具 ----------
    def _ch(self, seq):
        return self.rng.choice(seq)

    def _rand_price(self, base_price):
        if base_price is None:
            base_price = Decimal('19.99')
        return base_price

    # ---------- 用户 ----------
    def _ensure_users(self):
        User = get_user_model()
        users = []
        for i in range(1, self.n_users + 1):
            username = f'demo{i:02d}'
            u = User.objects.filter(username=username).first()
            if u is None:
                u = User.objects.create_user(
                    username=username,
                    email=f'{username}@carvenex.com',
                    password='CaravNex123!',
                    first_name=f'Demo{i}',
                    last_name='User',
                )
            self._ensure_profile(u)
            users.append(u)
        return users

    def _ensure_profile(self, user):
        try:
            from django.apps import apps
            model = apps.get_model('users', 'UserProfile')
        except LookupError:
            return
        if not model._default_manager.filter(user=user).exists():
            try:
                model.objects.create(user=user)
            except Exception:  # noqa: BLE001
                pass

    # ---------- 订单与订单项 ----------
    def _seed_orders(self):
        from apps.order.models import Order as _Order
        if _Order.objects.filter(user__username__startswith='demo').exists():
            self.stdout.write('  [订单] 已存在演示订单，跳过（避免幂等积压）')
            return 0
        statuses = ['pending_payment', 'paid', 'shipped', 'delivered', 'completed', 'cancelled']
        # 生成偏真实的时间：过去 120 天内按「每天随机订单数」分布，工作日偏多、周末偏少，
        # 且每天内的下单时刻散步在 8:00-23:00 之间（更接近真实购物行为），避免均匀铺在 90 天显得假。
        now = timezone.now()
        # 先算出过去 120 天每天的「随机订单数」（工作日偏多、周末偏少），再把每个订单的
        # 下单时刻摊散到 8:00-23:00 的随机分钟上，形成更真实的分布，而非均匀铺在 90 天。
        day_plans = []
        for day_offset in range(0, 120):
            dow = (now - timedelta(days=day_offset)).weekday()
            weekday_like = dow < 5  # 工作日
            # 周末单量低（0-2），工作日单量高（2-8）
            day_count = self.rng.randint(2, 8) if weekday_like else self.rng.randint(0, 2)
            for _ in range(day_count):
                minute = self.rng.randint(8 * 60, 22 * 60)  # 8:00-22:00 内随机分钟
                day_plans.append(now - timedelta(days=day_offset) + timedelta(minutes=minute))
        # 不足 320 单时，用 120 天之外的再往前补，保证总量达标
        while len(day_plans) < self.n_orders:
            day_offset = self.rng.randint(30, 130)
            minute = self.rng.randint(8 * 60, 22 * 60)
            day_plans.append(now - timedelta(days=day_offset) + timedelta(minutes=minute))
        self.rng.shuffle(day_plans)
        day_plans = day_plans[: self.n_orders]
        created = 0
        # 摊派：每个订单拿一个已计算好的时间戳；不足时 current
        for i in range(self.n_orders):
            user = self.rng.choice(self.users)
            sku = self.rng.choice(list(SKU.objects.filter(shelf_status='on')))
            spu = sku.spu
            price = sku.price or Decimal('19.99')
            discount_price = sku.discount_price
            qty = self.rng.randint(1, 3)
            subtotal = price * qty
            # 统一用 price 作为展示价，有折扣时用 discount_price
            unit = discount_price if (discount_price and discount_price > 0) else price
            subtotal = unit * qty
            total = subtotal
            status = self.rng.choice(statuses)
            # 按状态回填时间基准：用预计算的时间戳（保证每天分布真实、工作量可控）
            base = day_plans[i] if i < len(day_plans) else now

            order = Order.objects.create(
                user=user,
                status=status,
                total_amount=total,
                actual_amount=total,
                discount_amount=Decimal('0.00'),
                shipping_name=user.get_full_name() or user.username,
                shipping_phone='+1-555-0100',
                shipping_address={
                    'detail': '123 Demo Street',
                    'city': 'New York',
                    'country': 'US',
                    'zip': '10001',
                },
                currency='USD',
                payment_status=PaymentStatus.PAID if status != 'pending_payment' else PaymentStatus.UNPAID,
                payment_method='paypal' if status != 'pending_payment' else '',
                payment_no=f'PAY{self.rng.randint(100000, 999999)}' if status != 'pending_payment' else '',
                paid_at=base if status in ('paid', 'shipped', 'delivered', 'completed') else None,
                shipped_at=base if status in ('shipped', 'delivered', 'completed') else None,
                delivered_at=base if status in ('delivered', 'completed') else None,
                completed_at=base if status == 'completed' else None,
                cancelled_at=base if status == 'cancelled' else None,
                cancel_reason='Change of mind' if status == 'cancelled' else '',
                tracking_no=f'TK{self.rng.randint(100000, 999999)}' if status in ('shipped', 'delivered', 'completed') else '',
                created_at=base,
                updated_at=base,
            )
            # created_at 为 auto_now_add，save/create 时会被覆盖为「当前时间」；
            # 用 update() 绕过该行为，真正写入预计算的过去时间，形成真实分布。
            _Order.objects.filter(pk=order.pk).update(created_at=base, updated_at=base)
            OrderItem.objects.create(
                order=order,
                sku=sku,
                spu_name=spu.name,
                sku_name='Default',
                spec_snapshot=[],
                price=unit,
                quantity=qty,
                subtotal=subtotal,
            )
            created += 1
        self.stdout.write(f'  [订单] 生成 {created} 单')
        return created

    # ---------- 评价 ----------
    def _seed_reviews(self):
        from apps.review.models import Review
        created = 0
        for spu in self.spus:
            # 每个商品随机 0-5 条评价；同用户同商品只保留一条
            n = self.rng.randint(1, 5)
            for _ in range(n):
                user = self.rng.choice(self.users)
                if Review.objects.filter(user=user, spu=spu).exists():
                    continue
                rating = self.rng.choices([5, 4, 3, 2, 1], weights=[50, 25, 12, 8, 5])[0]
                Review.objects.create(
                    user=user, spu=spu,
                    rating=rating,
                    content=self._review_text(rating),
                    is_active=True,
                )
                created += 1
        self.stdout.write(f'  [评价] 生成 {created} 条')
        return created

    def _review_text(self, rating):
        texts = {
            5: 'Excellent quality and fast shipping. Highly recommended!',
            4: 'Very good product, works as described.',
            3: 'Decent value, shipping was a bit slow.',
            2: 'Not exactly as expected, but okay.',
            1: 'Disappointed with the quality.',
        }
        return texts.get(rating, 'Good product.')

    # ---------- 收藏 ----------
    def _seed_favorites(self):
        from apps.lovegoods.models import Favorite
        created = 0
        for user in self.users:
            # 每个用户收藏若干商品
            for spu in self.rng.sample(self.spus, k=min(6, len(self.spus))):
                _, was = Favorite.objects.get_or_create(user=user, spu=spu)
                if was:
                    created += 1
        self.stdout.write(f'  [收藏] 生成 {created} 条')
        return created

    # ---------- 购物车 ----------
    def _seed_carts(self):
        from apps.cart.models import Cart, CartItem
        created = 0
        for user in self.users:
            cart, _ = Cart.objects.get_or_create(user=user)
            skus = self.rng.sample(list(SKU.objects.filter(shelf_status='on')), k=min(3, SKU.objects.count()))
            for sku in skus:
                _, was = CartItem.objects.get_or_create(cart=cart, sku=sku,
                                                        defaults={'quantity': self.rng.randint(1, 2)})
                if was:
                    created += 1
        self.stdout.write(f'  [购物车] 生成 {created} 项')
        return created

    # ---------- 优惠券 ----------
    def _seed_coupons(self):
        from apps.promotion.models import Coupon, UserCoupon
        created = 0
        now = timezone.now()
        # 一张全场券 + 几张各面额
        coupon_defs = [
            {'name': 'New User 10% Off', 'discount_type': 'percent', 'amount': Decimal('10.00'),
             'min_amount': Decimal('0'), 'code': 'NEW10'},
            {'name': '$20 Off $100+', 'discount_type': 'fixed', 'amount': Decimal('20.00'),
             'min_amount': Decimal('100.00'), 'code': 'SAVE20'},
            {'name': 'Shipping Free', 'discount_type': 'fixed', 'amount': Decimal('5.00'),
             'min_amount': Decimal('0'), 'code': 'FREESHIP'},
        ]
        for d in coupon_defs:
            coupon, was = Coupon.objects.get_or_create(
                code=d['code'],
                defaults={
                    'name': d['name'],
                    'discount_type': d['discount_type'],
                    'amount': d['amount'],
                    'min_amount': d['min_amount'],
                    'max_discount': d.get('max_discount'),
                    'start_time': now - timedelta(days=30),
                    'end_time': now + timedelta(days=30),
                    'is_active': True,
                    'total_count': 1000,
                },
            )
            if was:
                created += 1
            # 给部分用户发券
            for user in self.rng.sample(self.users, k=self.rng.randint(1, len(self.users))):
                _, uc_was = UserCoupon.objects.get_or_create(user=user, coupon=coupon)
                if uc_was:
                    created += 1
        self.stdout.write(f'  [优惠券] 生成 {created} 张(含发放)')
        return created

    # ---------- 浏览历史 ----------
    def _seed_browse_history(self):
        from apps.tracking.models import BrowseHistory
        created = 0
        now = timezone.now()
        for user in self.users:
            for spu in self.rng.sample(self.spus, k=min(10, len(self.spus))):
                _, was = BrowseHistory.objects.get_or_create(
                    user=user, spu=spu,
                    defaults={'viewed_at': now - timedelta(days=self.rng.randint(0, 30), hours=self.rng.randint(0, 23))},
                )
                if was:
                    created += 1
        return created

    # ---------- 物流 ----------
    def _seed_logistics(self):
        from apps.logistics.models import Carrier, Shipment
        from apps.order.models import Order
        created = 0
        # 承运商
        carriers = []
        for code, name in [('ups', 'UPS'), ('dhl', 'DHL Express'), ('fedex', 'FedEx')]:
            c, was = Carrier.objects.get_or_create(code=code, defaults={'name': name, 'is_active': True})
            carriers.append(c)
            if was:
                created += 1
        # 为已发货/已送达/已完成订单补发货单
        shipped_status = ['shipped', 'delivered', 'completed']
        for o in Order.objects.filter(status__in=shipped_status):
            if Shipment.objects.filter(order=o).exists():
                continue
            carrier = self.rng.choice(carriers)
            Shipment.objects.create(
                order=o,
                carrier=carrier,
                tracking_no=o.tracking_no or f'Z{self.rng.randint(100000000, 999999999)}',
                status='delivered' if o.status in ('delivered', 'completed') else 'shipped',
                shipping_cost=Decimal('0.00'),
                shipped_at=o.shipped_at,
                actual_delivery=o.delivered_at,
                tracking_history=[
                    {'time': o.shipped_at.isoformat(), 'desc': 'Shipped'} if o.shipped_at else {},
                ],
            )
            created += 1
        self.stdout.write(f'  [物流] 生成 {created} 单(含承运商)')
        return created

    # ---------- 客服/支持对话 ----------
    # 一组「真实用户可能提出的问题」多语言模板（用户→客服），配上自然回复，
    # 替换掉原先只有一句英文问句的假数据，让会话看起来更贴近真实场景。
    _SUPPORT_QA = [
        {
            'subject_zh': '订单物流状态',
            'subject_en': 'Order shipping status',
            'subject_ar': 'حالة شحن الطلب',
            'q_zh': '你好，我前两天下的订单一直显示“待发货”，大概什么时候能发出？',
            'q_en': "Hi, my order has been 'pending shipment' for two days. When will it be shipped?",
            'q_ar': 'مرحباً، طلبي ما زال يظهر "قيد الشحن" منذ يومين. متى سيتم شحنه؟',
            'a_zh': '您好，非常抱歉让您久等了。您的订单已进入备货流程，预计明天内发出，发货后会在订单页面同步物流单号，请耐心等待。',
            'a_en': "Hi, sorry for the wait. Your order is being prepared and should ship within a day. You'll get the tracking number updated in your order once it ships.",
            'a_ar': 'عذراً على الانتظار. طلبكم قيد التجهيز وسيتم شحنه خلال يوم، وسنحدّث رقم التتبع في صفحة الطلب بعد الشحن.',
        },
        {
            'subject_zh': '发票开具',
            'subject_en': 'Invoice request',
            'subject_ar': 'طلب فاتورة',
            'q_zh': '你好，我在国内采购需要用发票报销，能否开具增值税发票？',
            'q_en': "Hi, I need an invoice for business reimbursement. Can you provide a VAT invoice?",
            'q_ar': 'مرحباً، أحتاج فاتورة لتسديد نفقات عملي، هل يمكنكم تزويدي بفاتورة ضريبية؟',
            'a_zh': '当然可以。请提供贵司抬头、税号和发票接收邮箱，我们会在订单完成后为您开具电子发票并发到邮箱。',
            'a_en': "Sure. Please share your company name, tax number and invoicing email, and we'll issue the invoice after the order is completed.",
            'a_ar': 'بالتأكيد. يرجى تزويدنا باسم شركتك والرقم الضريبي والبريد لتلقي الفاتورة، وسنقوم بإصدارها بعد اكتمال الطلب.',
        },
        {
            'subject_zh': '商品尺寸咨询',
            'subject_en': 'Product size question',
            'subject_ar': 'استفسار عن المقاس',
            'q_zh': '我喜欢这个雕刻机，但不确定尺寸是否适合我的桌面，能提供精确的长宽吗？',
            'q_en': "I like this engraver, but I'm not sure it fits my desk. Could you tell me the exact dimensions?",
            'q_ar': 'أعجبتني آلة النقش هذه، لكن لست متأكداً من مناسبتها لطاولتي، هل يمكنكم إخباري بالأبعاد الدقيقة؟',
            'a_zh': '您好，这款雕刻机机身尺寸约为 40×35×28cm，建议桌面预留至少 50×50cm。您也可以查看商品详情页的规格参数作参考。',
            'a_en': 'The machine body is about 40×35×28 cm; we recommend a desk space of at least 50×50 cm. You can also check the spec sheet on the product page.',
            'a_ar': 'يبلغ حجم الجهاز حوالي ٤٠×٣٥×٢٨ سم، وننصح بمساحة طاولة لا تقل عن ٥٠×٥٠ سم. يمكنك أيضاً الاطلاع على المواصفات في صفحة المنتج.',
        },
        {
            'subject_zh': '退款申请',
            'subject_en': 'Refund request',
            'subject_ar': 'طلب استرداد',
            'q_zh': '收到货后发现电源适配器是坏的，想申请退款或换新，该怎么操作？',
            'q_en': "The power adapter arrived broken. I'd like a refund or a replacement. What should I do?",
            'q_ar': 'وصلني محول طاقة تالف، وأرغب في إعادة المبلغ أو استبداله. ما الخطوات التي يجب أن أتبعها؟',
            'a_zh': '非常抱歉给您带来不便。您可以先在订单详情里发起“售后/退款”，上传损坏部件的照片，我们会在 24 小时内为您处理退款或补发。',
            'a_en': "Really sorry for the trouble. Please apply for after-sales/refund in your order detail with a photo of the damage; we'll process a refund or replacement within 24 hours.",
            'a_ar': 'نعتذر كثيراً عن هذا الإزعاج. نرجو التقدم بطلب ما-البعد-البيعي أو إعادة المبلغ من تفاصيل الطلب مع صورة للعطل، وسنعالجه خلال ٢٤ ساعة.',
        },
        {
            'subject_zh': '物流配送时间',
            'subject_en': 'Delivery time',
            'subject_ar': 'زمن التوصيل',
            'q_zh': '我下单很多天了，物流信息一直没有更新，麻烦帮我确认包裹到哪里了？',
            'q_en': "It's been days and my tracking hasn't updated. Could you check where my package is?",
            'q_ar': 'لقد مرت عدة أيام ولم يتحدث بيانات التتبع، هل يمكنكم التأكد من موقع الطرد الخاص بي؟',
            'a_zh': '已为您查询，包裹目前正在中转仓，预计 2-3 天内会到达派送点并更新最新的扫描记录。感谢您的理解。',
            'a_en': "I've checked; your package is at the transit hub and should reach the local delivery point within 2-3 days, where tracking will update.",
            'a_ar': 'لقد راجعت شحنتكم، وهي ماندٍ حالياً في مستودع التوصيل ومن المتوقع أن تصل إلى نقطة التوزيع خلال ٢-٣ أيام، حيث سيتم تحديث بيانات التتبع.',
        },
    ]

    def _seed_support(self):
        from apps.customer_service.models import Conversation, Message
        User = get_user_model()
        admin = User.objects.filter(is_superuser=True).first()
        created = 0
        for user in self.users:
            qa = self.rng.choice(self._SUPPORT_QA)
            subject = qa.get('subject_en', 'Order status question')
            conv, was = Conversation.objects.get_or_create(
                user=user, status='open',
                defaults={'subject': subject},
            )
            if was:
                Message.objects.create(
                    conversation=conv, sender=user,
                    sender_type='user', content=qa['q_en'],
                )
                if admin:
                    Message.objects.create(
                        conversation=conv, sender=admin,
                        sender_type='admin', content=qa['a_en'],
                    )
                created += 1
        return created

    def _any_admin(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.filter(is_superuser=True).first()