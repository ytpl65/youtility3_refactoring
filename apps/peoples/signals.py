
# @receiver(post_save, sender=People)
# def on_create_or_update_people_update_ticket_user(sender, instance, created, **kwargs):
#     tkt = rest2.Rt(url=settings.RT_URL, http_auth=requests.auth.HTTPBasicAuth(settings.RT_USERNAME, settings.RT_PASS))
#     user_kwargs = {
#         'Name':instance.loginid,
#         'RealName':instance.peoplename,
#         'EmailAddress':instance.email,
#         'MobilePhone':instance.mobno,

#     }
#     if tkt.user_exists(instance.loginid, privileged=False):
#         tkt.edit_user(instance.loginid, **user_kwargs)
#     else:
#         tkt.create_user(user_name=user_kwargs.pop('Name'), email_address=user_kwargs.pop('EmailAddress'), **user_kwargs)
