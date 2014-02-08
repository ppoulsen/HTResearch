from datetime import datetime
from mongoengine import Q
from mongoengine.fields import StringField

from dto import *

from connection import DBConnection
from HTResearch.DataModel.enums import OrgTypesEnum
from HTResearch.Utilities.geocoder import geocode
import re


class DAO(object):
    """
    A generic DAO class that may be subclassed by DAOs for operations on
    specific documents.
    """

    def __init__(self):
        self.conn = DBConnection

    def merge_documents(self, dto, merge_dto):
        with self.conn():
            attributes = merge_dto._data
            for key in attributes:
                if attributes[key] is not None:
                    cur_attr = getattr(dto, key)
                    if cur_attr is None:
                        setattr(dto, key, attributes[key])
                    else:
                        # TODO: Maybe we should merge all reference documents, as well?
                        pass

            dto.last_updated = datetime.utcnow()
            dto.save()
            return dto

    def create_update(self, dto):
        pass

    def delete(self, dto):
        with self.conn():
            dto.delete()

    # NOTE: This method will not return an object when
    # passed constraints that are reference types!
    def find(self, **constraints):
        with self.conn():
            return self.dto.objects(Q(**constraints) & self._valid_query()).first()

    def count(self, search=None, **constraints):
        with self.conn():
            # Do text search or grab by constraints
            if search is not None:
                return len(self._text_search(search, None))
            else:
                return self.dto.objects(Q(**constraints) & self._valid_query()).count()

    # NOTE: This method will not return an object when
    # passed constraints that are reference types!
    def findmany(self, num_elements=None, page_size=None, page=None, start=None, end=None, sort_fields=None,
                 search=None, search_fields=None, **constraints):
        with self.conn():
            # Do text search or grab by constraints
            if search is not None:
                ret = self._text_search(search, fields=search_fields)
            else:
                ret = self.dto.objects(Q(**constraints) & self._valid_query())

            # Sort if there are sort fields
            if sort_fields is not None and len(sort_fields) > 0:
                ret = ret.order_by(*sort_fields)

            if num_elements is not None:
                return ret[:num_elements]
            elif page_size is not None and page is not None:
                # as an example, if we want page 3 with a page size of 50, we want elements with index 150 to 199
                pg_start = page_size * page
                pg_end = page_size * (page + 1)
                # NOTE: Even though end would equal 200 in our example, python's slicing is not inclusive for end
                return ret[pg_start:pg_end]
            elif start is not None:
                if end is None:
                    return ret[start:]
                else:
                    return ret[start:end + 1]

            return ret

    # Query to get all valid objects
    def _valid_query(self):
        return Q()

    # Search string fields for text and return list of results
    def _text_search(self, text, fields):
        # Search default fields if none given
        if fields is None:
            fields = self._default_search_fields()
        entry_query = self._get_query(text, fields)
        found_entries = self.dto.objects(entry_query & self._valid_query())

        ob = self.dto.objects()[0]

        return found_entries

    # Create search term list from search string
    def _normalize_query(self, query_string,
                         findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                         normspace=re.compile(r'\s{2,}').sub):
        return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]

    # Get a query representing text search results
    def _get_query(self, query_string, search_fields):
        query = None # Query to search for every search term
        terms = self._normalize_query(query_string)
        for term in terms:
            or_query = None
            for field_name in search_fields:
                q = self._term_query(term, field_name)
                or_query = or_query | q if or_query else q
            query = query & or_query if query else or_query
        return query

    # Get a Q searching for a single term
    def _term_query(self, term, field_name):
        return Q(**{'%s__icontains' % field_name: term})

    # Default search fields: all string fields
    def _default_search_fields(self):
        return [key for key, value in self.dto._fields.iteritems() if isinstance(value, StringField)]


class ContactDAO(DAO):
    """
    A DAO for the Contact document
    """

    def __init__(self):
        super(ContactDAO, self).__init__()
        self.dto = ContactDTO

        # Injected dependencies
        self.org_dao = OrganizationDAO
        self.pub_dao = PublicationDAO

    def _add_contact_ref_to_children(self, contact_dto):
        if contact_dto.organization is not None and contact_dto not in contact_dto.organization.contacts:
            contact_dto.organization.contacts.append(contact_dto)
            contact_dto.organization = self.org_dao().create_update(contact_dto.organization, False)
        if contact_dto.publications is not None:
            for i in range(len(contact_dto.publications)):
                p = contact_dto.publications[i]
                if contact_dto not in p.authors:
                    p.authors.append(contact_dto)
                    contact_dto.publications[i] = self.pub_dao.create_update(p, False)
        return contact_dto

    def create_update(self, contact_dto, cascade_add=True):
        no_id = contact_dto.id is None
        with self.conn():
            if cascade_add:
                o = contact_dto.organization
                if o:
                    if contact_dto in o.contacts and no_id:
                        o.contacts.remove(contact_dto)
                    contact_dto.organization = self.org_dao().create_update(o, False)
                for i in range(len(contact_dto.publications)):
                    p = contact_dto.publications[i]
                    if contact_dto in p.authors and no_id:
                        p.authors.remove(contact_dto)
                    contact_dto.publications[i] = self.pub_dao().create_update(p, False)

            if no_id:
                existing_dto = self.dto.objects(email=contact_dto.email).first()
                if existing_dto is not None:
                    saved_dto = self.merge_documents(existing_dto, contact_dto)
                    if cascade_add:
                        saved_dto = self._add_contact_ref_to_children(saved_dto)
                    return saved_dto
            contact_dto.last_updated = datetime.utcnow()
            contact_dto.save()
        return contact_dto

    def _default_search_fields(self):
        return ['first_name', 'last_name', 'position', ]


class OrganizationDAO(DAO):
    """
    A DAO for the Organization document
    """

    def __init__(self):
        super(OrganizationDAO, self).__init__()
        self.dto = OrganizationDTO

        # Injected dependencies
        self.contact_dao = ContactDAO
        self.geocode = geocode

    def merge_documents(self, existing_org_dto, new_org_dto):
        with self.conn():
            attributes = new_org_dto._data
            for key in attributes:
                if attributes[key] or key == 'latlng':
                    cur_attr = getattr(existing_org_dto, key)
                    if not cur_attr:
                        if key == 'latlng' and not attributes['latlng'] and attributes['address']:
                            setattr(existing_org_dto, key, attributes[key])
                    elif type(cur_attr) is list:
                        merged_list = list(set(cur_attr + attributes[key]))
                        # if this is org types and we have more than one org type, make sure unknown isn't a type :P
                        if key == "types" and len(merged_list) > 1 and OrgTypesEnum.UNKNOWN in merged_list:
                            merged_list.remove(OrgTypesEnum.UNKNOWN)
                        setattr(existing_org_dto, key, attributes[key])

            existing_org_dto.last_updated = datetime.utcnow()
            existing_org_dto.save()
            return existing_org_dto

    def _add_org_ref_to_children(self, org_dto):
        for i in range(len(org_dto.contacts)):
            c = org_dto.contacts[i]
            if c.organization is None:
                c.organization = org_dto
                org_dto.contacts[i] = self.contact_dao().create_update(c, False)
        for i in range(len(org_dto.partners)):
            p = org_dto.partners[i]
            if org_dto not in p.partners:
                p.partners.append(org_dto)
                org_dto.partners[i] = self.create_update(p, False)
        return org_dto

    def create_update(self, org_dto, cascade_add=True):
        no_id = org_dto.id is None
        with self.conn():
            if cascade_add:
                for i in range(len(org_dto.contacts)):
                    c = org_dto.contacts[i]
                    if c.organization is not None and c.organization == org_dto:
                        c.organization = None
                    org_dto.contacts[i] = self.contact_dao().create_update(c, False)

                for i in range(len(org_dto.partners)):
                    p = org_dto.partners[i]
                    if org_dto in p.partners:
                        p.partners.remove(org_dto)
                    org_dto.partners[i] = self.create_update(p, False)

            if no_id:
                existing_dto = self._smart_search_orgs(org_dto)
                if existing_dto is not None:
                    saved_dto = self.merge_documents(existing_dto, org_dto)
                    if cascade_add:
                        saved_dto = self._add_org_ref_to_children(saved_dto)
                    return saved_dto
                elif org_dto.latlng is None and org_dto.address:
                    # Geocode it
                    org_dto.latlng = self.geocode(org_dto.address)

            org_dto.last_updated = datetime.utcnow()
            org_dto.save()
            if cascade_add:
                org_dto = self._add_org_ref_to_children(org_dto)
        return org_dto

    # Query getting valid organizations: must be valid and have a valid name
    def _valid_query(self):
        return Q(name__ne=None) & Q(name__ne='')

    # Query searching for organizations by a single term
    def _term_query(self, term, field_name):
        q = None
        if field_name == 'types':
            types = OrgTypesEnum.mapping.keys()
            matches = [OrgTypesEnum.mapping[type] for type in types if term.lower() in type.lower()]
            for match in matches:
                new_query = Q(types=match)
                q = q | new_query if q else new_query
        else:
            q = super(OrganizationDAO, self)._term_query(term, field_name)

        return q

    # Default fields for organization text searching
    def _default_search_fields(self):
        return ['name', 'keywords', 'address', 'types', ]

    def _smart_search_orgs(self, org_dto):
        # organizations have unique phone numbers
        if org_dto.phone_numbers:
            same_phone = Q(phone_numbers__in=org_dto.phone_numbers)
        else:
            same_phone = Q()

        # organizations have unique emails
        if org_dto.emails:
            same_email = Q(emails__in=org_dto.emails)
        else:
            same_email = Q()

        # organizations have unique URLs
        if org_dto.organization_url:
            same_url = Q(organization_url=org_dto.organization_url)
        else:
            same_url = Q()

        # organizations have unique Facebooks
        if org_dto.facebook:
            same_fb = Q(facebook=org_dto.facebook)
        else:
            same_fb = Q()

        # organizations have unique Twitters
        if org_dto.twitter:
            same_twitter = Q(twitter=org_dto.twitter)
        else:
            same_twitter = Q()

        # organizations have unique names
        if org_dto.name:
            same_name = Q(name=org_dto.name)
        else:
            same_name = Q()

        existing_dto = self.dto.objects(same_phone | same_email | same_url | same_fb | same_twitter | same_name).first()
        return existing_dto


class PublicationDAO(DAO):
    """
    A DAO for the Publication document
    """

    def __init__(self):
        super(PublicationDAO, self).__init__()
        self.dto = PublicationDTO

        # Injected dependencies
        self.contact_dao = ContactDAO

    def create_update(self, pub_dto, cascade_add=True):
        no_id = pub_dto.id is None
        with self.conn():
            if no_id:
                existing_dto = self.dto.objects(title=pub_dto.title).first()
                if existing_dto is not None:
                    saved_dto = self.merge_documents(existing_dto, pub_dto)
                    return saved_dto

            pub_dto.last_updated = datetime.utcnow()
            pub_dto.save()
        return pub_dto

    def _default_search_fields(self):
        return ['title', 'authors', ]


class URLMetadataDAO(DAO):
    """
    A DAO for the URLMetadata document
    """

    def __init__(self):
        super(URLMetadataDAO, self).__init__()
        self.dto = URLMetadataDTO

    def merge_documents(self, dto, merge_dto):
        with self.conn():
            attributes = merge_dto._data
            for key in attributes:
                if key == "last_visited":
                    cur_attr = getattr(dto, key)
                    if attributes[key] > cur_attr:
                        setattr(dto, key, attributes[key])
                elif attributes[key] is not None:
                    setattr(dto, key, attributes[key])
            dto.save()
            return dto

    def create_update(self, url_dto):
        with self.conn():
            if url_dto.id is None:
                existing_dto = self.dto.objects(url=url_dto.url).first()
                if existing_dto is not None:
                    saved_dto = self.merge_documents(existing_dto, url_dto)
                    return saved_dto

            url_dto.last_updated = datetime.utcnow()
            url_dto.save()
        return url_dto

    def findmany_by_domains(self, num_elements, required_domains, blocked_domains, *sort_fields):
        if len(required_domains) > 0:
            req_query = Q(domain__in=required_domains)
        else:
            req_query = Q()
        if len(blocked_domains) > 0:
            blk_query = Q(domain__nin=blocked_domains)
        else:
            blk_query = Q()

        with self.conn():
            if len(sort_fields) > 0:
                return URLMetadataDTO.objects(req_query & blk_query).order_by(*sort_fields)[:num_elements]
            else:
                return URLMetadataDTO.objects(req_query & blk_query)[:num_elements]


class UserDAO(DAO):
    def __init__(self):
        super(UserDAO, self).__init__()
        self.dto = UserDTO

        # Injected dependencies
        self.org_dao = OrganizationDAO

    def create_update(self, user_dto):
        with self.conn():
            if user_dto.organization is not None:
                o = user_dto.organization
                user_dto.organization = self.org_dao().create_update(o)

            user_dto.last_updated = datetime.utcnow()
            user_dto.save()
        return user_dto
