import inspect

from django.db import models

from smartlinks.index_conf import smartlinks_conf

def register(*configurations):
    """
    Register multiple smartlinks. Each ``conf`` in ``configurations`` is
    a tuple ``(shortcuts, conf)``, see :py:func:`register_smart_link`.
    """
    for (shortcuts, conf) in configurations:
        register_smart_link(shortcuts, conf)
    return smartlinks_conf


def register_smart_link(shortcuts, conf):
    """
    Registers the model as "smartlinkable" in the global dictionary smartlinks_conf
    and does the consistency checking.
    Usually the calls to this function will be done from models.py
    or urls.py modules at the configuration stage.

    EG::

        class Event(models.Model):
            title = models.CharField(max_length=400)

        smartlinks.register_smart_link(('e',), SmartLinkConf(queryset=Event.objects))

    will result in::

        smartlinks_conf = {'e': SmartLinkConf(queryset=Event.objects))

    Modifies smartlinks_conf.

    :param shortcuts: List of names which can be used to specify that
    smartlink should point to this particular class.
    :type shortcuts: Tuple of strings.

    :param conf: Smartlink configuration.
    :type conf: :py:class:`SmartLinkConf` instance.

    :throws:
        - IncorrectlyConfiguredSmartlinkException
        - AlreadyRegisteredSmartlinkException

    """
    model = conf.queryset.model

    # Sanity configuration checks.
    for fieldset in conf['searched_fields']:
        for fieldname in fieldset:
            if not hasattr(model, fieldname):
                raise IncorrectlyConfiguredSmartlinkException(
                    "Model '%s' does not have attribute '%s'" % (
                        model, fieldname
                        )
                )

            value = getattr(model, fieldname)
            if callable(value):
                arg_info = inspect.getargspec(value)

                # All functions which are returning the value for the
                # smartlink should have one and only one argument - 'self'.
                if len(arg_info.args) - len(arg_info.defaults) != 1:
                    raise IncorrectlyConfiguredSmartlinkException(
                        """Function '%s' in model '%s' configured as smartlink search
                        value has incorrect number of arguments.""" % (
                            fieldname, model
                        )
                    )

    # Make all provided shortcuts point to the same
    # configuration.
    for name in shortcuts:
        if name in smartlinks_conf:
            raise AlreadyRegisteredSmartlinkException()

        smartlinks_conf[name] = conf

    # Connect post-save/post-delete signals.
    for signal in [models.signals.post_save, models.signals.post_delete]:
        signal.connect(
            conf.update_index_for_object,
            sender=model
        )

    # The global object is updated as well,
    # this line is purely for debugging/testing purposes.
    return smartlinks_conf

class AlreadyRegisteredSmartlinkException(Exception):
    pass

class IncorrectlyConfiguredSmartlinkException(Exception):
    pass

