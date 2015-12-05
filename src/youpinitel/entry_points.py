#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import argparse
import os

from app import Application

__author__ = 'Eric Pascual'

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname).1s] %(name)s: %(message)s"
)


def demo_main():
    script_basename = 'youpinitel-demo'
    cfg_home = '/etc' if os.getuid() == 0 else '.youpinitel'

    parser = argparse.ArgumentParser(
        description="Youpi + Minitel demonstration"
    )
    parser.add_argument(
        '-m', '--minitel-port',
        help='device to which the Minitel is connected (default: %(default)s)',
        dest='minitel_port',
        default='/dev/ttyUSB0',
    )
    parser.add_argument(
        '-p', '--arm-port',
        help='device to which the arm interface is connected',
        dest='arm_port'
    )
    parser.add_argument(
        '-b', '--arm-busname',
        help='nROS bus name of the arm controller',
        dest='arm_busname'
    )
    parser.add_argument(
        '-c', '--config-file',
        help='configuration file (default: %(default)s)',
        dest='config_file',
        type=file,
        default=os.path.join(cfg_home, '%s.json' % script_basename),
    )
    parser.add_argument(
        '-d', '--debug',
        help='activates debug trace',
        action='store_true'
    )

    args = parser.parse_args()

    try:
        app = Application(log=logging.getLogger('app'), **args.__dict__)

    except Exception as e:
        if args.debug:
            logging.exception('unexpected error')
        logging.getLogger().fatal('unable to initialize application instance (%s)', e)

    else:
        try:
            app.run()
        except Exception as e:
            if args.debug:
                logging.exception('unexpected error')
            else:
                # logging.getLogger().fatal('unexpected error : (%s) %s', e.__class__.__name__, e)
                logging.getLogger().exception(e)
        else:
            logging.getLogger().info('application terminated')
