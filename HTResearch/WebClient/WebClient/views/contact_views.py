# stdlib imports
from django.shortcuts import render
from springpython.context import ApplicationContext
from django.http import HttpResponseRedirect

# project imports
from HTResearch.DataModel.enums import AccountType
from HTResearch.Utilities.context import DAOContext
from HTResearch.Utilities.logutil import LoggingSection, get_logger
from HTResearch.WebClient.WebClient.views.shared_views import get_http_404_page
from HTResearch.WebClient.WebClient.views.shared_views import unauthorized
from HTResearch.WebClient.WebClient.models import EditContactForm

#region Globals
logger = get_logger(LoggingSection.CLIENT, __name__)
ctx = ApplicationContext(DAOContext())
#endregion


def contact_profile(request, id):
    """
    Sends a request to the Contact Profile page and retrieves Contact information for the profile.

    Returns:
        A dictionary containing the Contact/User information.
    """
    user_id = request.session['user_id'] if 'user_id' in request.session else None

    logger.info('Request made for profile of contact={0} by user={1}'.format(id, user_id))

    user_dao = ctx.get_object('UserDAO')

    try:
        user = user_dao.find(id=id)

    except:
        logger.error('Exception encountered on user lookup for user={0}'.format(id))
        return get_http_404_page(request)

    if user and not user_id:
        logger.warn('Unauthorized request made for user={0}'.format(user.id))
        return unauthorized(request)

    contact_dao = ctx.get_object('ContactDAO')

    try:
        contact = contact_dao.find(id=id)
    except:
        logger.error('Exception encountered on contact lookup for contact={0}'.format(id))
        return get_http_404_page(request)

    if contact:
        results = contact.__dict__['_data']
    elif user:
        results = user.__dict__['_data']

    org_dao = ctx.get_object('OrganizationDAO')
    try:
        if results['organization']:
            org = org_dao.find(id=results['organization'].id)
            results['organization'] = org.__dict__['_data']
    except:
        logger.error('Exception encountered on organization lookup with search_text={0}'.format(results['organization'].name))
        return get_http_404_page(request)

    return render(request, 'contact/contact_profile.html', results)


def edit_contact(request, contact_id):
    """
    Sends a request to the Edit Contact page if the user is logged in and has a contributor account type.

    Returns:
        A dictionary containing the form, contact id, and success/error flags.
    """
    if 'user_id' not in request.session:
        return HttpResponseRedirect('/login')
    elif 'account_type' not in request.session or request.session['account_type'] != AccountType.CONTRIBUTOR:
        return HttpResponseRedirect('/')
    else:
        user_id = request.session['user_id']

    contact_dao = ctx.get_object('ContactDAO')

    error = ''
    success = ''

    try:
        contact = contact_dao.find(id=contact_id)
    except:
        logger.error('Exception encountered on contact lookup for contact={0} by user={1}'.format(contact_id, user_id))
        return get_http_404_page(request)

    phones = contact.phones if contact.phones else []

    form = EditContactForm(request.POST or None,
                           initial=_create_contact_dict(contact),
                           phones=phones)

    if request.method == 'POST':
        if form.is_valid():
            data = form.cleaned_data
            new_phones = []

            if 'invalid' in data:
                contact.valid = not data['invalid']

            try:
                for key, value in data.items():
                    if key.startswith('phone'):
                        new_phones.append(value.strip())
                    else:
                        setattr(contact, key, value.strip()) if value else setattr(contact, key, None)
            except:
                error = 'Oops! Something went wrong processing your request. Please try again later.'
                logger.error('Error occurred while updating fields for contact={0} by user={1}'.format(contact_id, user_id))

            if not error:
                if new_phones:
                    contact.phones = [p for p in new_phones if p]

                try:
                    contact_dao.create_update(contact)
                    success = 'The contact has been updated successfully!'
                    logger.info('Contact={0} updated by user={1}'.format(contact_id, user_id))
                except:
                    error = 'Oops! There was an error updating the contact. Please try again soon.'

    return render(request, 'contact/edit_contact.html', {'form': form, 'contact_id': contact_id,
                                                         'success': success, 'error': error})


def _create_contact_dict(contact):
    """
    Helper function to convert a ContactDAO to a dictionary.

    Arguments:
        contact (ContactDAO): The contact that is being converted.

    Returns:
        A { string : string } dictionary of ContactDAO fields.
    """
    contact_dict = {'first_name': contact.first_name if contact.first_name else "",
                    'last_name': contact.last_name if contact.last_name else "",
                    'email': contact.email if contact.email else "",
                    'position': contact.position if contact.position else "",
                    'invalid': not contact.valid}
    return contact_dict
