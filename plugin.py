###
# Copyright (c) 2013-2014, spline
# All rights reserved.
#
#
###
# libs
import os
import re
import tailer
from tbgrep import TracebackGrep
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
    _ = PluginInternationalization('LogTail')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x


class LogTail(callbacks.Plugin):
    """Add the help for "@plugin help LogTail" here
    This should describe *how* to use this plugin."""
    threaded = True

    #############################
    # INTERNAL HELPER FUNCTIONS #
    #############################
        
    def _grep(self, pattern, file_obj, ln=False):
        """
        grep-like function
        """

        l = []
        for i, line in enumerate(open(file_obj).readlines()):
            if re.match(pattern, line):
                if ln:
                    l.append("{0} {1}".format(i+i, line.rstrip()))
                else:
                    l.append(line.rstrip())
        return l

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

    def _gS(self, fn):
        """File size wrapper."""

        st = os.stat(fn)
        num = st.st_size
        # pretty.
        for x in ['b','KB','MB','GB']:
            if num < 1024.0 and num > -1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, 'TB')

    ###################
    # PUBLIC COMMANDS #
    ###################

    def grep(self, irc, msg, args, optlog, optpat):
        """<log> <pattern>
        
        Grep logfile for pattern.
        """
        
        optlog = optlog.lower()

        # next, grab our list of logs.
        ll = self._listlogs()
        if not ll:
            irc.reply("ERROR: No logs found to display.")
            return
        else:  # found logs. verify it works.
            if optlog not in ll:  # we didn't find. display a list.
                irc.reply("ERROR: '{0}' is not a valid log. These are: {1}".format(optlog, " | ".join([i for i in ll.keys()])))
                return
        # now find.
        g = self._grep(optpat, ll[optlog], ln=False)
        # we get a list back.
        if len(g) == 0:  # no matches.
            irc.reply("Sorry, I found no matches in the {0} logfile for '{1}'".format(optlog, optpat))
        else:  # matches.
            irc.reply(g)

    grep = wrap(grep, [('checkCapability', 'owner'), ('somethingWithoutSpaces'), ('text')])

    def tbgrep(self, irc, msg, args, optlist, optlog):
        """[--options] <logfile>
        
        Display tracebacks from a specific logfile.
        """

        # first, lower optlog to match.
        optlog = optlog.lower()
        
        # next handle optlist.
        lines, showlast = 10, False  # defaults.
        if optlist:
            for (k, v) in optlist:
                if k == 'last':
                    showlast = True
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
        tbo = []
        # now lets use TracebackGrep.
        extractor = TracebackGrep()
        for line in file(ll[optlog]):
            tb = extractor.process(line)
            if tb:  # if we find any, add.        
                tbo.append(tb)
                #irc.reply(type(tb))
        # now lets output if we find anything.
        if len(tbo) == 0:
            irc.reply("I did not find any Tracebacks in {0}'s logfile.".format(optlog))
        else:  # found some. how to handle.
            if showlast:
                irc.reply("{0}".format(tbo[-1]))
            else:
                for each in tbo[-(lines):]:
                    irc.reply(each)
            
    tbgrep = wrap(tbgrep, [('checkCapability', 'owner'), getopts({'last':'', 'n':('int') }), ('somethingWithoutSpaces')])

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
        lf = tailer.tail(open(ll[optlog]), lines)
        # lets display.
        if singleline:
            irc.reply("{0} :: {1}".format(optlog, " ".join([i for i in lf])))
        else:  # one per line.
            for l in lf:
                irc.reply("{0}".format(l))

    tail = wrap(tail, [('checkCapability', 'owner'), getopts({'singleline': '', 'n':('int') }), ('somethingWithoutSpaces')])

    def rmlog(self, irc, msg, args, optlog):
        """<log>
        
        Deletes logfile.
        """

        # first, lower optlog to match.
        optlog = optlog.lower()

        # next, grab our list of logs.
        ll = self._listlogs()
        if not ll:
            irc.reply("ERROR: No logs found to display.")
            return
        else:  # found logs. verify it works.
            if optlog not in ll:  # we didn't find. display a list.
                irc.reply("ERROR: '{0}' is not a valid log. These are: {1}".format(optlog, " | ".join([i for i in ll.keys()])))
                return
        # now lets delete the log.
        fn = ll[optlog]  # filname
        fs = self._gS(fn)  # filesize.
        # now lets try to delete.
        try:
            os.remove(fn)
            irc.reply("I have successfully removed {0} ({1})".format(fn, fs))
        except Exception as e:
            irc.reply("ERROR trying to delete {0} :: {1}".format(fn, e))

    rmlog = wrap(rmlog, [('checkCapability', 'owner'), ('somethingWithoutSpaces')])

    def listlogs(self, irc, msg, args, optlist):
        """[--size]
        
        List log files available. Use --size to display how big.
        """
        
        # setup input args.
        s = False
        if optlist:
            for (k, v) in optlist:
                if k == "size":
                    s = True
        
        # grab and go.
        ll = self._listlogs()
        if not ll:
            irc.reply("ERROR: No logs found to display.")
        else:
            for (k, v) in ll.items():
                if s:  # filesize.
                    irc.reply("{0} :: {1} :: {2}".format(k, self._gS(v),  v))
                else:  # no size.
                    irc.reply("{0} :: {1}".format(k, v))

    listlogs = wrap(listlogs, [('checkCapability', 'owner'), getopts({'size': ''})])

Class = LogTail


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
