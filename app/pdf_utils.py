import io
import calendar
from datetime import date
from django.utils import timezone
from django.db.models import Sum

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from .models import CallHistory, WithdrawalRequest, Transaction, User


def generate_agent_paysheet_pdf(agent: User, year: int = None, month: int = None) -> io.BytesIO:
    """
    Generates a professional, branded PDF paysheet for an agent for the specified month/year.
    Returns an in-memory BytesIO buffer containing the PDF bytes.
    """
    now = timezone.localtime(timezone.now())
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    # Calculate date boundaries for the selected month
    last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    month_name = date(year, month, 1).strftime("%B %Y")
    issue_date = now.strftime("%B %d, %Y, %I:%M %p")
    paysheet_ref = f"HM-PAY-{year}{month:02d}-{agent.id:04d}"

    # 1. Agent Details
    profile = getattr(agent, 'profile', None)
    agent_name = profile.name if (profile and profile.name) else agent.username
    agent_phone = agent.phone_number or (profile.phone_number if profile else "-") or "-"
    agent_email = agent.email or "-"
    joined_date = timezone.localtime(agent.date_joined).strftime("%b %d, %Y") if agent.date_joined else "-"
    agent_status = (agent.agent_status or "active").upper()

    # 2. Call Performance in this period
    completed_calls = CallHistory.objects.filter(
        receiver=agent,
        status='completed',
        start_time__date__gte=start_date,
        start_time__date__lte=end_date
    )

    audio_calls = completed_calls.filter(call_type='audio')
    video_calls = completed_calls.filter(call_type='video')

    audio_count = audio_calls.count()
    video_count = video_calls.count()
    total_calls_count = audio_count + video_count

    # Calculate duration
    def calc_duration(queryset):
        return sum(c.duration for c in queryset if c.duration)

    audio_duration_secs = calc_duration(audio_calls)
    video_duration_secs = calc_duration(video_calls)
    total_duration_secs = audio_duration_secs + video_duration_secs

    def format_duration(seconds):
        if not seconds:
            return "0m 00s"
        hrs = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        if hrs > 0:
            return f"{hrs}h {mins}m {secs}s"
        return f"{mins}m {secs}s"

    # Call coins earned
    call_coins = sum(c.coins_earned for c in completed_calls if c.coins_earned)
    # Check transaction ledger if calls have 0 recorded coins_earned
    txn_call_coins = Transaction.objects.filter(
        user=agent,
        transaction_type='earn_call',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_coins_earned = max(call_coins, txn_call_coins)

    # 3. Withdrawals during this period
    withdrawals = WithdrawalRequest.objects.filter(
        agent=agent,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).order_by('created_at')

    approved_withdrawals = withdrawals.filter(status='approved')
    total_withdrawn_coins = approved_withdrawals.aggregate(total=Sum('amount'))['total'] or 0

    # 4. Current Wallet Balance
    current_balance = agent.wallet.balance if hasattr(agent, 'wallet') else agent.coins
    net_period_change = total_coins_earned - total_withdrawn_coins

    # --- Build PDF Document ---
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    brand_style = ParagraphStyle(
        'BrandStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#8B5CF6')
    )
    brand_sub = ParagraphStyle(
        'BrandSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )
    title_style = ParagraphStyle(
        'PaysheetTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0F172A')
    )
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F172A')
    )
    cell_regular = ParagraphStyle(
        'CellRegular',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    cell_muted = ParagraphStyle(
        'CellMuted',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#64748B')
    )
    cell_right = ParagraphStyle(
        'CellRight',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#0F172A')
    )
    footer_text = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#94A3B8')
    )

    elements = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>NAMMAL</b>", brand_style),
            Paragraph(f"<b>PAYSHEET STATEMENT</b><br/><font color='#64748B'>Ref: {paysheet_ref}</font>", ParagraphStyle('HRef', parent=title_style, alignment=TA_RIGHT, fontSize=12, leading=15))
        ],
        [
            Paragraph("Agent Earnings & Activity Statement", brand_sub),
            Paragraph(f"Statement Period: <b>{month_name}</b><br/>Generated: {issue_date}", ParagraphStyle('HDate', parent=cell_muted, alignment=TA_RIGHT))
        ]
    ]
    header_table = Table(header_data, colWidths=[280, 260])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 14))

    # Divider Line
    line_table = Table([['']], colWidths=[540], rowHeights=[2])
    line_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#8B5CF6')),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 14))

    # 2. Agent Information Card
    agent_info_data = [
        [
            Paragraph("<b>Agent Name:</b>", cell_bold),
            Paragraph(agent_name, cell_regular),
            Paragraph("<b>Agent ID:</b>", cell_bold),
            Paragraph(f"#{agent.id}", cell_regular),
        ],
        [
            Paragraph("<b>Username:</b>", cell_bold),
            Paragraph(f"@{agent.username}", cell_regular),
            Paragraph("<b>Agent Status:</b>", cell_bold),
            Paragraph(f"<font color='#10B981'><b>{agent_status}</b></font>", cell_regular),
        ],
        [
            Paragraph("<b>Phone:</b>", cell_bold),
            Paragraph(agent_phone, cell_regular),
            Paragraph("<b>Joined Platform:</b>", cell_bold),
            Paragraph(joined_date, cell_regular),
        ],
        [
            Paragraph("<b>Email:</b>", cell_bold),
            Paragraph(agent_email, cell_regular),
            Paragraph("<b>Statement Month:</b>", cell_bold),
            Paragraph(month_name, cell_regular),
        ],
    ]
    info_table = Table(agent_info_data, colWidths=[85, 185, 95, 175])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    # 3. Call Performance & Call Earnings Breakdown
    elements.append(Paragraph("1. CALL PERFORMANCE & EARNINGS", section_title))
    elements.append(Spacer(1, 6))

    calls_data = [
        [
            Paragraph("<b>Call Type</b>", cell_bold),
            Paragraph("<b>Completed Calls</b>", cell_bold),
            Paragraph("<b>Total Duration</b>", cell_bold),
            Paragraph("<b>Coins Earned</b>", cell_right),
        ],
        [
            Paragraph("Audio Calls", cell_regular),
            Paragraph(str(audio_count), cell_regular),
            Paragraph(format_duration(audio_duration_secs), cell_regular),
            Paragraph(f"{audio_count * 0} Coins" if total_coins_earned == 0 else "—", cell_right),
        ],
        [
            Paragraph("Video Calls", cell_regular),
            Paragraph(str(video_count), cell_regular),
            Paragraph(format_duration(video_duration_secs), cell_regular),
            Paragraph(f"{video_count * 0} Coins" if total_coins_earned == 0 else "—", cell_right),
        ],
        [
            Paragraph("<b>Total Call Activity</b>", cell_bold),
            Paragraph(f"<b>{total_calls_count} calls</b>", cell_bold),
            Paragraph(f"<b>{format_duration(total_duration_secs)}</b>", cell_bold),
            Paragraph(f"<b>+{total_coins_earned:,} Coins</b>", ParagraphStyle('TotalCallCoins', parent=cell_right, textColor=colors.HexColor('#10B981'))),
        ],
    ]
    calls_table = Table(calls_data, colWidths=[150, 120, 140, 130])
    calls_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EDE9FE')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F5F3FF')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(calls_table)
    elements.append(Spacer(1, 16))

    # 4. Withdrawals & Payouts in this Month
    elements.append(Paragraph("2. WITHDRAWALS & PAYOUTS PROCESSED", section_title))
    elements.append(Spacer(1, 6))

    withdrawals_rows = [
        [
            Paragraph("<b>Request ID</b>", cell_bold),
            Paragraph("<b>Date Requested</b>", cell_bold),
            Paragraph("<b>Status</b>", cell_bold),
            Paragraph("<b>Amount (Coins)</b>", cell_right),
        ]
    ]

    if withdrawals.exists():
        for w in withdrawals:
            status_color = '#10B981' if w.status == 'approved' else ('#EF4444' if w.status == 'rejected' else '#F59E0B')
            withdrawals_rows.append([
                Paragraph(f"REQ-#{w.id:04d}", cell_regular),
                Paragraph(timezone.localtime(w.created_at).strftime("%b %d, %Y %I:%M %p"), cell_regular),
                Paragraph(f"<font color='{status_color}'><b>{w.status.title()}</b></font>", cell_regular),
                Paragraph(f"{w.amount:,} Coins", cell_right),
            ])
    else:
        withdrawals_rows.append([
            Paragraph("<i>No withdrawal requests were submitted in this period.</i>", cell_muted),
            Paragraph("", cell_regular),
            Paragraph("", cell_regular),
            Paragraph("0 Coins", cell_right),
        ])

    withdrawals_rows.append([
        Paragraph("<b>Total Approved Withdrawals</b>", cell_bold),
        Paragraph("", cell_regular),
        Paragraph("", cell_regular),
        Paragraph(f"<b>-{total_withdrawn_coins:,} Coins</b>", ParagraphStyle('TotalWithdraw', parent=cell_right, textColor=colors.HexColor('#EF4444'))),
    ])

    withdrawals_table = Table(withdrawals_rows, colWidths=[130, 160, 120, 130])
    withdrawals_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EDE9FE')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FEF2F2')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(withdrawals_table)
    elements.append(Spacer(1, 16))

    # 5. Financial Summary Box (Totals)
    elements.append(Paragraph("3. FINANCIAL SUMMARY", section_title))
    elements.append(Spacer(1, 6))

    summary_data = [
        [
            Paragraph("Gross Period Earnings (from calls)", cell_regular),
            Paragraph(f"<b>+{total_coins_earned:,} Coins</b>", ParagraphStyle('G1', parent=cell_right, textColor=colors.HexColor('#10B981')))
        ],
        [
            Paragraph("Processed / Approved Withdrawals", cell_regular),
            Paragraph(f"<b>-{total_withdrawn_coins:,} Coins</b>", ParagraphStyle('G2', parent=cell_right, textColor=colors.HexColor('#EF4444')))
        ],
        [
            Paragraph("<b>Net Period Activity</b>", cell_bold),
            Paragraph(f"<b>{net_period_change:+,} Coins</b>", ParagraphStyle('G3', parent=cell_right, textColor=colors.HexColor('#8B5CF6')))
        ],
        [
            Paragraph("<b>Current Available Wallet Balance</b>", cell_bold),
            Paragraph(f"<b>{current_balance:,} Coins</b>", ParagraphStyle('G4', parent=cell_right, fontSize=11, textColor=colors.HexColor('#0F172A')))
        ],
    ]
    summary_table = Table(summary_data, colWidths=[380, 160])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#F5F3FF')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#EDE9FE')),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#8B5CF6')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 24))

    # 6. Authorization & Sign-off Footer
    sign_data = [
        [
            Paragraph("<b>Authorized By:</b>", cell_bold),
            Paragraph("<b>Agent Acceptance:</b>", cell_bold),
        ],
        [
            Paragraph("Nammal Platform Superadmin<br/><font color='#64748B'>Digitally Verified & Approved</font>", cell_muted),
            Paragraph(f"{agent_name}<br/><font color='#64748B'>Registered Agent Account</font>", cell_muted),
        ],
    ]
    sign_table = Table(sign_data, colWidths=[270, 270])
    sign_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(sign_table)
    elements.append(Spacer(1, 16))

    # 7. Platform Disclaimer
    elements.append(Paragraph(
        "This is an official computer-generated statement issued by Nammal. Coins earned are credited per platform terms. For payout queries, contact administration.",
        footer_text
    ))

    # Build the document
    doc.build(elements)
    buffer.seek(0)
    return buffer
