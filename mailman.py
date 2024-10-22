import subprocess


def send_email(kerb, to_address, subject, body):
    """
    Send an email (using msmtp).

    Returns nothing, but may raise an OSError(msmtp exit code, msmtp stderr)
    """
    command = [
        "msmtp",  # What sendmail on Athena calls
        "--host=outgoing.mit.edu",
        "--port=587",
        "--auth=gssapi",  # Authenticate with kerberos
        f"--from={kerb}@mit.edu",
        f"--user={kerb}@ATHENA.MIT.EDU",
        "-v",  # Verbose, may be helpful for debugging (TODO: remove)
        to_address,
    ]
    email = "\n".join([f"Subject: {subject}", f"{body}"])
    # We are only capturing stderr
    result = subprocess.run(
        command, input=email, encoding="utf-8", stderr=subprocess.PIPE
    )
    if result.returncode != 0:
        raise OSError(result.returncode, result.stderr)


def command_email_address(list_name):
    return f"{list_name}-request@mit.edu"


# EMAIL_BODY = (
#     "This is an automated email to request {request} the {list_name} list. "
#     "It was sent to {list_name}-request@mit.edu, a bot email address that accepts commands. "
#     "You should never email {list_name}@mit.edu to request to be subscribed or unsubscribed, "
#     "as that goes to everyone subscribed to the list."
# )


def mailman_request_subscription(kerb, list_name):
    """
    Request to be subscribed to a Mailman list.
    """
    to_addr = command_email_address(list_name)
    # uncommenting the body for now since it shows up in the
    #   "The results of your email commands" email, which may be confusing.
    #   It also seems like the sent email is not copied to the "Sent" folder.
    # body = EMAIL_BODY.format(request="to be subscribed to", list_name=list_name)
    body = ""
    send_email(kerb, to_addr, "subscribe", body)


def mailman_request_unsubscription(kerb, list_name):
    """
    Request to be unsubscribed to a Mailman list.
    """
    to_addr = command_email_address(list_name)
    # body = EMAIL_BODY.format(request="unsubscription", list_name=list_name)
    body = ""
    send_email(kerb, to_addr, "unsubscribe", body)
