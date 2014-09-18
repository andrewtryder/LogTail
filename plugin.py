###
# Copyright (c) 2013-2014, spline
# All rights reserved.
#
#
###
# libs
import os
import re
from collections import deque, defaultdict
from operator import itemgetter
# extra supybot libs.
import supybot.conf as conf
import supybot.schedule as schedule
# supybot libs
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Logger')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x


class Logger(callbacks.Plugin):
    """Add the help for "@plugin help Logger" here
    This should describe *how* to use this plugin."""
    threaded = True


    def __init__(self, irc):
        self.__parent = super(Logger, self)
        self.__parent.__init__(irc)
        self.logfiles = None
        self.logdir = None

    def cachelogfiles(self):
        """This will check if we have individual logfiles and cache
        the proper filenames."""

        # NOTE, we could also use a list of loaded Plugins -> .log + construct.
        self.log.info("CacheLogFiles: Running")
        # make sure we're using individual logfiles.
        if not conf.supybot.log.plugins.individualLogfiles():
            self.log.error("ERROR: config log.plugins.individualLogfiles True")
            self.log.error("Must be set for this plugin to work.")
            return
        # next, verify the existance of the logdirectory.
        pluginlogs = conf.supybot.directories.log()+'/plugins'
        if not os.path.exists(pluginlogs):
            self.log.error("ERROR: {0} path does not exist.".format(pluginlogs))
            return
        # now that we have the dir, grab the files and parse.
        # must be a file, match File.regex (ignores Channel.ignore.log). lower + strip.
        matchinglogs = [f for f in os.listdir(pluginlogs) if os.path.isfile(os.path.join(pluginlogs, f)) and re.match('^\w+.log$', f)]
        if len(matchinglogs) != 0:  # if not 0, change self.logfiles.
            self.logfiles = matchinglogs
            self.logdir = pluginlogs
        else:
            self.log.error("ERROR: I did not find any matching Plugin log files in {0}".format(logdir))

    def _tail2(self, logfile, n=1, bs=1024):
        f = open(logfile)
        f.seek(-1,2)
        l = 1-f.read(1).count('\n') # If file doesn't end in \n, count it anyway.
        B = f.tell()
        while n >= l and B > 0:
                block = min(bs, B)
                B -= block
                f.seek(B, 0)
                l += f.read(block).count('\n')
        f.seek(B, 0)
        l = min(l,n) # discard first (incomplete) line if l > n
        lines = f.readlines()[-l:]
        f.close()
        return lines

    def _tail(self, filename, n=None):
        """Return the last n lines of a file."""

        if not n:
            n = 20

        return deque(open(filename), n)

    def _findexceptions(self, filename):
        """Grep through filename and return a list of exceptions."""

        filehandle = open(filename).read()  # read in. regex below.
        exceptions = re.findall('(ERROR.*?Uncaught exception.*?)ERROR', filehandle, re.M|re.S)
        exceptionlist = []  # list to dump in.
        # return None if we don't find anything.
        if not exceptions:
            return None
        else:  # each one is appended in to list.
            for e in exceptions:
                exceptionlist.append(e)
            # now return the list.
            return exceptionlist

    def loggrep(self, restring, strlist):
        """grep"""

        expr = re.compile(restring)
        return filter(expr.search, strlist)

    # INFO 2013-06-10T11:04:11 tail called in private by "spline!spline@percolator.mrcoffee.org".
    #def tailtracebacks(self, irc, msg, args, optlog):
    #tailtracebacks = wrap(tailtracebacks, [('somethingWithoutSpaces')])

    def logblah(self, irc, msg, args):
        """
        .
        """

        irc.reply(fffff)

    logblah = wrap(logblah)

    def _filecheck(self, optfile):

        logfile = self.logdir + '/' + optfile
        return logfile

    # http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
    # http://stackoverflow.com/questions/3168759/python-parsing-files/3168786#3168786

    def logtail(self, irc, msg, args, optlog):
        """<logfile>

        Tail's a logfile. 10 lines.
        """

        if not self.logfiles and not self.logdir:
            irc.reply("ERROR: Something broke on logfiles and logdir.")
            return

        if optlog not in self.logfiles:
            irc.reply("ERROR: '{0}' not in logfiles.".format(optlog))
            return

        optlog = self._filecheck(optlog)

        filetail = self._tail2(optlog, n=10)
        for line in filetail:
            irc.reply(line.strip('\n'))

    logtail = wrap(logtail, [('somethingWithoutSpaces')])


    def tail(self, irc, msg, args, optlog):
        """
        Log Tail.
        """

        logs = conf.supybot.directories.log()
        pluginlogs = logs+'/plugins'
        matchinglogs = [f for f in os.listdir(pluginlogs) if os.path.isfile(os.path.join(pluginlogs, f)) and re.match('^\w+.log$', f)]
        if optlog in matchinglogs:
            fulllog = pluginlogs+'/'+optlog
            irc.reply("{0}".format(fulllog))
            extractor = TracebackGrep()
            for line in file(fulllog):
                tb = extractor.process(line)
                if tb:
                    irc.reply(tb)
        else:
            irc.reply("Sorry, I did not find {0}".format(optlog))

    tail = wrap(tail, [('somethingWithoutSpaces')])


    def logger(self, irc, msg, args):
        """
        Docstring.
        """

        logoption = conf.supybot.log.plugins.individualLogfiles()
        irc.reply(logoption)

        # if not os.path.exists
        logs = conf.supybot.directories.log()
        irc.reply(logs)
        pluginlogs = logs+'/plugins'

        matchinglogs = [f for f in os.listdir(pluginlogs) if os.path.isfile(os.path.join(pluginlogs, f)) and re.match('^\w+.log$', f)]
        irc.reply(matchinglogs)

    logger = wrap(logger)

Class = Logger


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
