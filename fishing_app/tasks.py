from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_purchase_confirmation_email(user_email, username, item_name, category):
    subject = 'Purchase Confirmation'
    message = f'Dear {username},\n\nYou have successfully purchased {item_name} in the category {category}.\n\nThank you for your purchase!'
    from_email = 'your-email@gmail.com'
    recipient_list = [user_email]

    # 发送邮件
    send_mail(subject, message, from_email, recipient_list)
