import cStringIO
import uuid
import threading
import time
import os

# Solution for detecting when the Selenium standalone server is ready to go by
# listening to its console output.  Obtained from
# http://stackoverflow.com/questions/3076542/how-can-i-read-all-availably-data-from-subprocess-popen-stdout-non-blocking/3078292#3078292


class InputStreamChunker(threading.Thread):
    """
    Threaded object / code that mediates reading output from a stream,
    detects "separation markers" in the stream and spits out chunks
    of original stream, split when ends of chunk are encountered.

    Results are made available as a list of filled file-like objects
    (your choice). Results are accessible either "asynchronously"
    (you can poll at will for results in a non-blocking way) or
    "synchronously" by exposing a "subscribe and wait" system based
    on threading.Event flags.

    Usage:

    * instantiate this object
    * give our input pipe as "stdout" to other subprocess and start it::
          Popen(..., stdout = th.input, ...)
    * (optional) subscribe to data_available event
    * pull resulting file-like objects off .data (if you are "messing" with
      .data from outside of the thread, be courteous and wrap the
      thread-unsafe manipulations between::

          obj.data_unoccupied.clear()
          ... mess with .data
          obj.data_unoccupied.set()

      The thread will not touch obj.data for the duration and will block
      reading.)

    License: Public domain
    Absolutely no warranty provided
    """
    def __init__(self, delimiter=None, outputObjConstructor=None):
        """
        delimiter - the string that will be considered a delimiter for the
        stream outputObjConstructor - instances of these will be attached to
        self.data array (intantiator_pointer, args, kw)
        """
        super(InputStreamChunker, self).__init__()

        self._data_available = threading.Event()
        self._data_available.clear()  # parent will .wait() on this for results
        self._data = []
        self._data_unoccupied = threading.Event()
        self._data_unoccupied.set()  # parent will set this to true when self.results is being changed from outside
        self._r, self._w = os.pipe()  # takes all inputs. self.input = public pipe in.
        self._stop = False
        if not delimiter:
            delimiter = str(uuid.uuid1())
        self._stream_delimiter = [l for l in delimiter]
        self._stream_roll_back_len = (len(delimiter) - 1) * -1
        if not outputObjConstructor:
            self._obj = (cStringIO.StringIO, (), {})
        else:
            self._obj = outputObjConstructor

    @property
    def data_available(self):
        """returns a threading.Event instance pointer that is
        True (and non-blocking to .wait() ) when we attached a
        new IO obj to the .data array.
        Code consuming the array may decide to set it back to False
        if it's done with all chunks and wants to be blocked on .wait()"""
        return self._data_available

    @property
    def data_unoccupied(self):
        """returns a threading.Event instance pointer that is normally
        True (and non-blocking to .wait() ) Set it to False with .clear()
        before you start non-thread-safe manipulations (changing) .data
        array. Set it back to True with .set() when you are done"""
        return self._data_unoccupied

    @property
    def data(self):
        """returns a list of input chunkes (file-like objects) captured
        so far. This is a "stack" of sorts. Code consuming the chunks
        would be responsible for disposing of the file-like objects.
        By default, the file-like objects are instances of cStringIO"""
        return self._data

    @property
    def input(self):
        """This is a file descriptor (not a file-like).
        It's the input end of our pipe which you give to other process
        to be used as stdout pipe for that process"""
        return self._w

    def flush(self):
        """Normally a read on a pipe is blocking.
        To get things moving (make the subprocess yield the buffer,
        we inject our chunk delimiter into self.input

        This is useful when primary subprocess does not write anything
        to our in pipe, but we need to make internal pipe reader let go
        of the pipe and move on with things.
        """
        os.write(self._w, ''.join(self._stream_delimiter))

    def stop(self):
        self._stop = True
        self.flush()  # reader has its teeth on the pipe. This makes it let go for for a sec.
        os.close(self._w)
        self._data_available.set()

    def __del__(self):
        try:
            self.stop()
        except:
            pass
        try:
            del self._w
            del self._r
            del self._data
        except:
            pass

    def run(self):
        """ Plan:

        * We read into a fresh instance of IO obj until marker encountered.
        * When marker is detected, we attach that IO obj to "results" array
          and signal the calling code (through threading.Event flag) that
          results are available
        * repeat until .stop() was called on the thread.
        """
        marker = ['' for l in self._stream_delimiter]  # '' is there on purpose
        tf = self._obj[0](*self._obj[1], **self._obj[2])
        while not self._stop:
            l = os.read(self._r, 1)
            marker.pop(0)
            marker.append(l)
            if marker != self._stream_delimiter:
                tf.write(l)
            else:
                # chopping off the marker first
                tf.seek(self._stream_roll_back_len, 2)
                tf.truncate()
                tf.seek(0)
                self._data_unoccupied.wait(5)  # seriously, how much time is needed to get your items off the stack?
                self._data.append(tf)
                self._data_available.set()
                tf = self._obj[0](*self._obj[1], **self._obj[2])
        os.close(self._r)
        tf.close()
        del tf


class OutputMonitor:
    """
    Configure an output stream which can tell when a particular string has
    appeared.
    """

    def __init__(self):
        self.stream = InputStreamChunker('\n')
        self.stream.daemon = True
        self.stream.start()
        self.lines = []

    def wait_for(self, text, seconds):
        """
        Returns True when the specified text has appeared in a line of the
        output, or False when the specified number of seconds have passed
        without that occurring.
        """
        found = False
        stream = self.stream
        start_time = time.clock()
        while not found:
            stream.data_available.wait(0.5)
            stream.data_unoccupied.clear()
            while stream.data:
                line = stream.data.pop(0)
                value = line.getvalue()
                if text in value:
                    found = True
                self.lines.append(value)
                stream.data_available.clear()
                stream.data_unoccupied.set()
                if time.clock() - start_time > seconds:
                    break
        return found
