from app.config.cplog import CPLog
from app.lib.provider.yarr.base import nzbBase
from dateutil.parser import parse
from urllib import urlencode
from urllib2 import URLError
import time
import traceback

log = CPLog(__name__)

class nzbindexnl(nzbBase):
    """Api for nzbindexnl"""

    name = 'nzbindexnl'
    #http://nzbindex.nl/rss/?q=planet+der+affen&sort=agedesc&max=25
    #downloadUrl = 'https://nzbs.org/index.php?action=getnzb&nzbid=%s%s'
    #nfoUrl = 'https://nzbs.org/index.php?action=view&nzbid=%s&nfo=1'
    detailUrl = 'https://nzbs.org/index.php?action=view&nzbid=%s'
    apiUrl = 'http://nzbindex.nl/rss/'

    catIds = {
        4: ['720p', '1080p'],
        2: ['cam', 'ts', 'dvdrip', 'tc', 'brrip', 'r5', 'scr'],
        9: ['dvdr']
    }
    catBackupId = 't2'

    timeBetween = 3 # Seconds

    def __init__(self, config):
        log.info('Using Nzbindex.nl provider')

        self.config = config

    def conf(self, option):
        return self.config.get('nzbindexnl', option)

    def enabled(self):
        return self.conf('enabled') and self.config.get('nzbindexnl', 'enabled')

    def find(self, movie, quality, type, retry = False):

        self.cleanCache();

        results = []
        if not self.enabled() or not self.isAvailable(self.apiUrl):
            return results
        
        log.info('type %s .' % type)
        
        catId = self.getCatId(type)
        arguments = urlencode({
            'sort':'agedesc',
            'max':'100',
            'minsize':'400',
            'q': self.toSearchString(movie.name),
        })
        url = "%s?%s" % (self.apiUrl, arguments)
        cacheId = str(movie.imdb) + '-' + str(catId)
        singleCat = (len(self.catIds.get(catId)) == 1 and catId != self.catBackupId)

        try:
            cached = False
            if(self.cache.get(cacheId)):
                data = True
                cached = True
                log.info('Getting RSS from cache: %s.' % cacheId)
            else:
                log.info('Searching: %s' % url)
                data = self.urlopen(url)
                self.cache[cacheId] = {
                    'time': time.time()
                }
        except (IOError, URLError):
            log.error('Failed to open %s.' % url)
            return results

        if data:
            log.debug('Parsing nzbindex.nl RSS.')
            try:
                try:
                    if cached:
                        xml = self.cache[cacheId]['xml']
                    else:
                        xml = self.getItems(data)
                        self.cache[cacheId]['xml'] = xml
                except:
                    if retry == False:
                        log.error('No valid xml, to many requests? Try again in 15sec.')
                        time.sleep(15)
                        return self.find(movie, quality, type, retry = True)
                    else:
                        log.error('Failed again.. disable %s for 15min.' % self.name)
                        self.available = False
                        return results

                for item in xml:

                    id = int(self.gettextelement(item, "link").split('/')[4])

                    size = self.gettextelement(item, "description").split('</font><br />\n<b>')[1].split('<')[0]

                    new = self.feedItem()
                    new.id = id
                    new.type = 'nzb'
                    new.name = self.gettextelement(item, "title")
                    new.date = int(time.mktime(parse(self.gettextelement(item, "pubDate")).timetuple()))
                    new.size = self.parseSize(size)
                    new.url = "http://nzbindex.nl/download/"+str(id)
                    new.detailUrl = self.gettextelement(item, "guid")
                    new.content = ""#self.gettextelement(item, "guid")
                    new.score = self.calcScore(new, movie)

                    if self.isCorrectMovie(new, movie, type, singleCategory = singleCat):
                        results.append(new)
                        log.info('Found: %s' % new.name)

                return results
            except:
                log.error('Failed to parse XML response from nzbindex.nl: %s' % traceback.format_exc())
                return False

        return results


    def getApiExt(self):
        return '&i=%s&h=%s' % (self.conf('id'), self.conf('key'))
