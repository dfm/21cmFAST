Developer Documentation
=======================

If you are new to developing ``21cmFAST``, please read the :ref:`contributing:Contributing`
section *first*, which outlines the general concepts for contributing to development,
and provides a step-by-step walkthrough for getting setup.
This page lists some more detailed notes which may be helpful through the
development process.

Compiling for debugging
-----------------------
When developing, it is usually a good idea to compile the underlying C code in ``DEBUG``
mode. This may allow extra print statements in the C, but also will allow running the C
under ``valgrind`` or ``gdb``. To do this::

    $ DEBUG=True pip install -e .

See :ref:`installation:Installation` for more installation options.

Developing the C Code
---------------------
In this section we outline how one might go about modifying/extending the C code and
ensuring that the extension is compatible with the wrapper provided here. It is
critical that you run all tests after modifying _anything_ (and see the section
below about running with valgrind). When changing C code, before
testing, ensure that the new C code is compiled into your environment by running::

    $ rm -rf build
    $ pip install .

Note that using a developer install (`-e`) is not recommended as it stores compiled
objects in the working directory which don't get updated as you change code, and can
cause problems later.

There are two main purposes you may want to write some C code:

1. An external plugin/extension which uses the output data from 21cmFAST.
2. Modifying the internal C code of 21cmFAST.

21cmFAST currently provides no support for external plugins/extensions. It is entirely
possible to write your own C code to do whatever you want with the output data, but we
don't provide any wrapping structure for you to do this, you will need to write your
own. Internally, 21cmFAST uses the `cffi` library to aid the wrapping of the C code into
Python. You don't need to do the same, though we recommend it. If your desired
"extension" is something that needs to operate in-between steps of 21cmFAST, we also
provide no support for this, but it is possible, so long as the next step in the
chain maintains its API. You would be required to re-write the low-level wrapping
function _preceding_ your inserted step as well. For instance, if you had written a
self-contained piece of code that modified the initial conditions box, adding some
physical effect which is not already covered, then you would need to write a low-level
wrapper _and_ re-write the ``initial_conditions`` function to modify the box before
returning it. We provide no easy "plugin" system for doing this currently. If your
external code is meant to be inserted _within_ a basic step of 21cmFAST, this is
currently not possible. You will instead have to modify the source code itself.

Modifying the C-code of 21cmFAST should be relatively simple. If your changes are
entirely internal to a given function, then nothing extra needs to be done. A little
more work has to be done if the modifications add/remove input parameters or the output
structure. If any of the input structures are modified (i.e. an extra parameter
added to it), then the corresponding class in ``py21cmfast.wrapper`` must be modified,
usually simply to add the new parameter to the ``_defaults_`` dict with a default value.
For instance, if a new variable ``some_param`` was added to the ``user_params`` struct
in the ``ComputeInitialConditions`` C function, then the ``UserParams`` class in
the wrapper would be modified, adding ``some_param=<default_value>`` to its `_default_`
dict. If the default value of the parameter is dependent on another parameter, its
default value in this dict can be set to ``None``, and you can give it a dynamic
definition as a Python ``@property``. For example, the ``DIM`` parameter of
``UserParams`` is defined as::

    @property
    def DIM(self):
        if self._some_param is None:
            return self._DIM or 4 * self.HII_DIM

Note the underscore in ``_DIM`` here: by default, if a dynamic property is defined for
a given parameter, the ``_default_`` value is saved with a prefixed underscore. Here we
return either the explicitly set ``DIM``, or 4 by the ``HII_DIM``. In addition, if the
new parameter is not settable -- if it is completely determined by other parameters --
then don't put it in ``_defaults_`` at all, and just give it a dynamic definition.

If you modify an output struct, which usually house a number of array quantities
(often float pointers, but not necessarily), then you'll again need to modify the
corresponding class in the wrapper. In particular, you'll need to add an entry for that
particular array in the ``_init_arrays`` method for the class. The entry consists of
initialising that array (usually to zeros, but not necessarily), and setting its proper
dtype. All arrays should be single-pointers, even for multi-dimensional data. The latter
can be handled by initalising the array as a 1D numpy array, but then setting its shape
attribute (after creation) to the appropriate n-dimensional shape (see the
``_init_arrays`` method for the ``InitialConditions`` class for examples of this).

Modifying the ``global_params`` struct should be relatively straightforward, and no
changes in the Python are necessary. However, you may want to consider adding the new
parameter to relevant ``_filter_params`` lists for the output struct wrapping classes in
the wrapper. These lists control which global parameters affect which output structs,
and merely provide for more accurate caching mechanisms.

C Function Standards
~~~~~~~~~~~~~~~~~~~~
The C-level functions are split into two groups -- low-level "private" functions, and
higher-level "public" or "API" functions. All API-level functions are callable from
python (but may also be called from other C functions). All API-level functions are
currently prototyped in `21cmFAST.h`.

To enable consistency of error-checking in Python (and a reasonable standard for any
kind of code), we enforce that any API-level function must return an integer status.
Any "return" objects must be modified in-place (i.e. passed as pointers). This enables
Python to control the memory access of these variables, and also to receive proper
error statuses (see below for how we do exception handling). We also adhere to the
convention that "output" variables should be passed to the function as its last
argument(s). In the case that _only_ the last argument is meant to be "output", there
exists a simple wrapper `_call_c_simple` in `wrapper.py` that will neatly handle the
calling of the function in an intuitive pythonic way.

Running with Valgrind
~~~~~~~~~~~~~~~~~~~~~
If any changes to the C code are made, it is ideal to run tests under valgrind, and
check for memory leaks. To do this, install ``valgrind`` (we have tested v3.14+),
which is probably available via your package manager. We provide a
suppression file for ``valgrind`` in the ``devel/`` directory of the main repository.

It is ideal if you install a development-version of python especially for running these
tests. To do this, download the version of python you want and then configure/install with::

    $ ./configure --prefix=<your-home>/<directory> --without-pymalloc --with-pydebug --with-valgrind
    $ make; make install

Construct a ``virtualenv`` on top of this installation, and create your environment,
and install all requirements.

If you do not wish to run with a modified version of python, you may continue with your
usual version, but may get some extra cruft in the output. If running with Python
version > 3.6, consider running with environment variable ``PYTHONMALLOC=malloc``
(see https://stackoverflow.com/questions/20112989/how-to-use-valgrind-with-python ).

The general pattern for using valgrind with python is::

    $ valgrind --tool=memcheck --track-origins=yes --leak-check=full --suppressions=devel/valgrind-suppress-all-but-c.supp <python script>

One useful command is to run valgrind over the test suite (from the top-level repo
directory)::

    $ valgrind --tool=memcheck --track-origins=yes --leak-check=full --suppressions=devel/valgrind-suppress-all-but-c.supp pytest

While we will attempt to keep the suppression file updated to the best of our knowledge
so that only relevant leaks and errors are reported, you will likely have to do a bit of
digging to find the relevant parts.

Valgrind will likely run very slowly, and sometimes  you will know already which exact
tests are those which may have problems, or are relevant to your particular changes.
To run these::

    $ valgrind --tool=memcheck --track-origins=yes --leak-check=full --suppressions=devel/valgrind-suppress-all-but-c.supp pytest -v tests/<test_file>::<test_func>

Producing Integration Test Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
There are bunch of so-called "integration tests", which rely on previously-produced
data. To produce this data, run `python tests/produce_integration_test_data.py`.

Furthermore, this data should only be produced with good reason -- the idea is to keep
it static while the code changes, to have something steady to compare to. If a particular
PR fixes a bug which affects a certain tests' data, then that data should be re-run, in
the context of the PR, so it can be explained.

Logging in C
~~~~~~~~~~~~
The C code has a header file ``logging.h``. The C code should *never* contain bare
print-statements -- everything should be formally logged, so that the different levels
can be printed to screen correctly. The levels are defined in ``logging.h``, and include
levels such as ``INFO``, ``WARNING`` and ``DEBUG``. Each level has a corresponding macro
that starts with ``LOG_``. Thus to log run-time information to stdout, you would use
``LOG_INFO("message");``. Note that the message does not require a final newline character.

Exception handling in C
~~~~~~~~~~~~~~~~~~~~~~~
There are various places that things can go wrong in the C code, and they need to be
handled gracefully so that Python knows what to do with it (rather than just quitting!).
We use the simple ``cexcept.h`` header file from http://www.nicemice.net/cexcept/ to
enable a simple form of exception handling. That file itself should **not be edited**.
There is another header -- ``exceptions.h`` -- that defines how we use exceptions
throughout ``21cmFAST``. Any time an error arises that can be understood, the developer
should add a ``Throw <ErrorKind>;`` line. The ``ErrorKind`` can be any of the kinds
defined in ``exceptions.h`` (eg. ``GSLError`` or ``ValueError``). These are just integers.

Any C function that has a header in ``21cmFAST.h`` -- i.e. any function that is callable
directly from Python -- *must* be globally wrapped in a ``Try {} Catch(error_code) {}`` block. See
``GenerateICs.c`` for an example. Most of the code should be in the ``Try`` block.
Anything that does a ``Throw`` at any level of the call stack within that ``Try`` will
trigger a jump to the ``Catch``. The ``error_code`` is the integer that was thrown.
Typically, one will perhaps want to do some cleanup here, and then finally *return* the
error code.

Python knows about the exit codes it can expect to receive, and will raise Python
exceptions accordingly. From the python side, two main kinds of exceptions could be
raised, depending on the error code returned from C. The lesser exception is called a
``ParameterError``, and is supposed to indicate an error that happened merely because
the parameters that were input to the calculation were just too extreme to handle.
In the case of something like an automatic Monte Carlo algorithm that's iterating over
random parameters, one would *usually* want to just keep going at this point, because
perhaps it just wandered too far in parameter space.
The other kind of error is a ``FatalCError``, and this is where things went truly wrong,
and probably will do for any combination of parameters.

If you add a kind of Exception in the C code (to ``exceptions.h``), then be sure to add
a handler for it in the ``_process_exitcode`` function in ``wrapper.py``.
