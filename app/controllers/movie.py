from app.config.db import Session as Db, Movie
from app.controllers import BaseController, url, redirect
import cherrypy
import logging

log = logging.getLogger(__name__)

qMovie = Db.query(Movie)

class MovieController(BaseController):

    @cherrypy.expose
    @cherrypy.tools.mako(filename = "movie/index.html")
    def index(self):
        '''
        Show all wanted, snatched, downloaded movies
        '''

        movies = qMovie.order_by(Movie.name).filter_by(status = u'want').all()
        snatched = qMovie.order_by(Movie.name).filter_by(status = u'snatched').all()
        downloaded = qMovie.order_by(Movie.name).filter_by(status = u'downloaded').all()

        return self.render({'movies': movies, 'snatched':snatched, 'downloaded':downloaded})


    @cherrypy.expose
    def delete(self, id):
        '''
        Mark movie as deleted
        '''

        movie = qMovie.filter_by(id = id).one()

        #delete feeds
        #[Db.delete(x) for x in movie.Feeds]

        #set status
        movie.status = u'deleted'

        Db.flush()

        return redirect(url(controller = 'movie', action = 'index'))


    @cherrypy.expose
    def downloaded(self, id):
        '''
        Mark movie as downloaded
        '''

        movie = qMovie.filter_by(id = id).one()

        #delete feeds
        #[Db.delete(x) for x in movie.Feeds]

        #set status
        movie.status = u'downloaded'

        Db.flush()

        return redirect(url(controller = 'movie', action = 'index'))


    @cherrypy.expose
    def reAdd(self, id):
        '''
        Re-add movie and force search
        '''

        movie = qMovie.filter_by(id = id).one()

        #set status
        movie.status = u'want'

        Db.flush()

        #gogo find nzb for added movie via Cron
        self.cron.get('nzb')._searchNzb(movie)

        return redirect(url(controller = 'movie', action = 'index'))


    @cherrypy.expose
    @cherrypy.tools.mako(filename = "movie/search.html")
    def search(self, **data):
        '''
        Search for added movie. 
        Add if only 1 is found
        '''
        movie = data.get('movie')
        movienr = data.get('movienr')
        quality = data.get('quality')
        year = data.get('year')

        log.info('Searching for: %s', movie)

        if data.get('add'):
            results = cherrypy.session['results']
            result = results[int(movienr)]

            if result.year != 'None' or year:
                self._addMovie(result, quality, year)
                return redirect(url(controller = 'movie', action = 'index'))
        else:
            results = self.searchers.get('movie').find(movie)
            cherrypy.session['results'] = results

        return self.render({'movie':movie, 'results': results, 'quality':quality})

    @cherrypy.expose
    @cherrypy.tools.mako(filename = "movie/imdbAdd.html")
    def imdbAdd(self, **data):
        '''
        Add movie by imdbId
        '''

        id = data.get('id')
        success = False

        result = qMovie.filter_by(imdb = id, status = u'want').first()
        if result:
            success = True

        if data.get('add'):
            result = self.searchers.get('movie').findByImdbId(id)

            self._addMovie(result, data.get('quality'), data.get('year'))
            log.info('Added : %s', result.name)
            success = True

        return self.render({'id':id, 'result':result, 'success':success, 'year':data.get('year')})


    def _addMovie(self, movie, quality, year = None):
        log.info('Adding movie to database: %s', movie.name)

        if movie.id:
            exists = qMovie.filter_by(movieDb = movie.id).first()
        else:
            exists = qMovie.filter_by(imdb = movie.imdb).first()
        if exists:
            log.info('Movie already exists, do update.')
            new = exists
        else:
            new = Movie()
            Db.add(new)

        new.status = u'want'
        new.name = movie.name
        new.imdb = movie.imdb
        new.movieDb = movie.id
        new.quality = quality

        # Year from custom input
        if year and movie.year == 'None':
            new.year = year
        else:
            new.year = movie.year

        Db.flush()

        #gogo find nzb for added movie via Cron
        self.cron.get('nzb')._searchNzb(new)
