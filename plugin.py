###
# Copyright (c) 2013-2014, spline
# All rights reserved.
#
#
###
# libs
import os
import re
# extra supybot libs.
import supybot.conf as conf
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

    def _grep(self, p, f):
        """
        grep-like function
        """

        r=[]
        for line in f:
            if re.search(p, line):
                r.append(line)
        return r

    def tailf(self, logfile, n):
        """
        code via: http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
        """

        bs = 1024
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
        # sed.
        lines = [i.replace("\n", '') for i in lines]
        f.close()
        return lines


    def tail(self, irc, msg, args, optlist, optlog):
        """[--singleline --n=# of lines] <logfile>
        
        Tail's the last 10 messages from a logfile. Execute listlogs command for a list of logs available.
        Ex: main
        """
        
        # first, lower optlog to match.
        optlog = optlog.lower()
        
        # next handle optlist.
        singleline, lines = False, 10  # defaults.
        if optlist:
            for (k, v) in optlist:
                if k == 'singleline':
                    singleline = True
                if k == 'n':
                    if v > 50:
                        irc.reply("Sorry, I won't display more than 50 lines.")
                    elif v < 1:
                        irc.reply("Sorry, I need a positive integer here.")
                    else:  # under 50 so lets go.
                        lines = v
            
        
        # next, grab our list of logs.
        ll = self._listlogs()
        if not ll:
            irc.reply("ERROR: No logs found to display.")
            return
        else:  # found logs. verify it works.
            if optlog not in ll:  # we didn't find. display a list.
                irc.reply("ERROR: '{0}' is not a valid log. These are: {1}".format(optlog, " | ".join([i for i in ll.keys()])))
                return
        # we're here if things worked.
        # lets display the last 10 lines.
        lf = self.tailf(ll[optlog], lines)
        # lets display.
        if singleline:
            irc.reply("{0} :: {1}".format(optlog, " ".join([i for i in lf])))
        else:  # one per line.
            for l in lf:
                irc.reply("{0}".format(l))

    tail = wrap(tail, [getopts({'singleline': '', 'n':('int') }), ('somethingWithoutSpaces')])


    def _listlogs(self):
        """
        List the available logs for tailing and display.
        """

        # container for out.
        l = {}
        # Do we have individual log files? (Boolean)
        ilf = conf.supybot.log.plugins.individualLogfiles()
        # if not os.path.exists
        logs = conf.supybot.directories.log()
        if not os.path.exists(logs):
            self.log.info("_listlogs :: Logs path ({0}) does not exist.".format(logs))
            return None
        # does individual logs exist?
        if ilf:
            ilflogs = logs+'/plugins'
            if not os.path.exists(ilflogs):
                self.log.reply("_listlogs :: ILF path ({0}) does not exist.".format(ilflogs))
        # now lets find the logs.
        mlf = logs+'/messages.log'
        # main log first.
        if os.path.isfile(mlf):
            l['main'] = mlf
        else:
            self.log.reply("_listlogs :: main log file ({0}) does not exist.".format(mlf))
            return None
        # now if we have individual log files, lets add those.
        if ilf:
            matchinglogs = [f for f in os.listdir(ilflogs) if os.path.isfile(os.path.join(ilflogs, f)) and re.match('^\w+.log$', f)]
            # list with matching. lets add these into the l dict. ex: Logger.log
            for i in matchinglogs:
                n = i.replace('.log', '').lower()  # remove .log and lower to match.
                l[n] = ilflogs + '/' + i  # path.
        # now return.
        if len(l) == 0:
            self.log.info("_listlogs :: ERROR no logs found.")
            return None
        else:
            return l

    def listlogs(self, irc, msg, args):
        """
        List log files available.
        """
        
        ll = self._listlogs()
        if not ll:
            irc.reply("ERROR: No logs found to display.")
        else:
            for (k, v) in ll.items():
                irc.reply("{0} :: {1}".format(k, v))

    listlogs = wrap(listlogs)

Class = Logger


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
