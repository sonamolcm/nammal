from django.contrib import admin
from .models import User, Profile, Offer, UserActivity, CallHistory, Notification

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Offer)
admin.site.register(UserActivity)
admin.site.register(CallHistory)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_audience', 'recipient', 'sent_count', 'failed_count', 'created_at')
    list_filter = ('target_audience', 'created_at')
    search_fields = ('title', 'body', 'recipient__username')

