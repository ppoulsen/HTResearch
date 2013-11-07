from mongoengine import Q
from dto import *
from connection import DBConnection
from mongoengine.fields import StringField, URLField


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
            return self.dto.objects(**constraints).first()

    # NOTE: This method will not return an object when
    # passed constraints that are reference types!
    def findmany(self, num_elements, *sort_fields, **constraints):
        with self.conn():
            if len(sort_fields) > 0:
                return self.dto.objects(**constraints).order_by(*sort_fields)[:num_elements]
            else:
                return self.dto.objects(**constraints)[:num_elements]

    # Search all string fields for text and return list of results
    # NOTE: may be slower than MongoDB's text search feature, which is unfortunately unusable because it is in beta
    def text_search(self, text, num_elements, *sort_fields):
        with DBConnection():
            # Find all string fields
            fields_dict = self.dto._fields
            string_types = (StringField, URLField)
            search_fields = [key for key in fields_dict.iterkeys() if type(fields_dict[key]) in string_types]

            # Search for each term in all string fields
            result_lists = []
            for term in text.split():
                results = [list(self.dto.objects(**{field + '__icontains': term})) for field in search_fields]
                results = reduce(lambda x, y: x + y, results)  # flatten to list of results
                result_lists.append(results)

            # Search by "AND" with search terms (change to any if you want "OR")
            combo = all
            results = []
            if result_lists:
                results = [item for item in result_lists[0] if combo(item in list for list in result_lists)]

            # Remove duplicates
            results = list(set(results))

            # sort by fields
            if sort_fields:
                for field in reversed(sort_fields):
                    results.sort(key=lambda result: result[field])

            # return the last num_elements
            return results[:num_elements]


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

    def create_update(self, contact_dto):
        with self.conn():
            for i in range(len(contact_dto.organizations)):
                o = contact_dto.organizations[i]
                contact_dto.organizations[i] = self.org_dao().create_update(o)
            for i in range(len(contact_dto.publications)):
                p = contact_dto.publications[i]
                contact_dto.publications[i] = self.pub_dao().create_update(p)

            if contact_dto.id is None:
                existing_dto = self.dto.objects(email=contact_dto.email).first()
                if existing_dto is not None:
                    saved_dto = self.merge_documents(existing_dto, contact_dto)
                    return saved_dto

            contact_dto.save()
        return contact_dto


class OrganizationDAO(DAO):
    """
    A DAO for the Organization document
    """
    def __init__(self):
        super(OrganizationDAO, self).__init__()
        self.dto = OrganizationDTO

        # Injected dependencies
        self.contact_dao = ContactDAO

    def create_update(self, org_dto):
        with self.conn():
            for i in range(len(org_dto.contacts)):
                c = org_dto.contacts[i]
                org_dto.contacts[i] = self.contact_dao().create_update(c)

            if org_dto.id is None:
                existing_dto = self.dto.objects(email_key__in=org_dto.emails).first()
                if existing_dto is not None:
                    saved_dto = self.merge_documents(existing_dto, org_dto)
                    return saved_dto

            org_dto.save()
        return org_dto


class PublicationDAO(DAO):
    """
    A DAO for the Publication document
    """
    def __init__(self):
        super(PublicationDAO, self).__init__()
        self.dto = PublicationDTO

        # Injected dependencies
        self.contact_dao = ContactDAO

    def create_update(self, pub_dto):
        with self.conn():
            for i in range(len(pub_dto.authors)):
                c = pub_dto.authors[i]
                pub_dto.authors[i] = self.contact_dao().create_update(c)

            if pub_dto.id is None:
                existing_dto = self.dto.objects(title=pub_dto.title).first()
                if existing_dto is not None:
                    saved_dto = self.merge_documents(existing_dto, pub_dto)
                    return saved_dto

            if pub_dto.publisher is not None:
                self.contact_dao().create_update(pub_dto.publisher)

            pub_dto.save()
        return pub_dto


class URLMetadataDAO(DAO):
    """
    A DAO for the URLMetadata document
    """
    def __init__(self):
        super(URLMetadataDAO, self).__init__()
        self.dto = URLMetadataDTO

    def create_update(self, url_dto):
        with self.conn():
            if url_dto.id is None:
                existing_dto = self.dto.objects(url=url_dto.url).first()
                if existing_dto is not None:
                    saved_dto = self.merge_documents(existing_dto, url_dto)
                    return saved_dto

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
