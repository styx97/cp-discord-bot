class Contest:
    __slots__ = ('name', 'site_tag', 'site_name', 'url', 'start', 'length')

    def __init__(self, name, site_tag, site_name, url, start, length):
        """
        Represents a competitive programming contest.

        :param name: the name of the contest
        :param site_tag: the site tag
        :param site_name: the site name
        :param url: the URL of the contest
        :param start: the timestamp of the UTC start time
        :param length: the length of the contest in seconds
        """

        self.name = name
        self.site_tag = site_tag
        self.site_name = site_name
        self.url = url
        self.start = start
        self.length = length

    def __lt__(self, other):
        return (self.start, self.length, self.site_name) < (other.start, other.length, other.site_name)

    def __repr__(self):
        return '<Contest' + str((self.name, self.site_tag, self.site_name, self.url, self.start, self.length)) + '>'


class Profile:
    __slots__ = ('handle', 'site_tag', 'site_name', 'url', 'name', 'rating')

    def __init__(self, handle, site_tag, site_name, url, name, rating):
        """
        Represents a user of a competitive programming site.

        :param handle: the user's handle
        :param site_tag: the site tag
        :param site_name: the site name
        :param url: the URL of the profile
        :param name: the user's full name, ``None`` if unavailable
        :param rating: the user's current rating, ``None`` if unrated
        """

        self.handle = handle
        self.site_tag = site_tag
        self.site_name = site_name
        self.url = url
        self.name = name
        self.rating = rating

    @classmethod
    def from_dict(cls, profile_dict):
        params = [profile_dict.get(key) for key in cls.__slots__]
        return Profile(*params)

    def to_dict(self):
        return {key: getattr(self, key) for key in self.__slots__}
