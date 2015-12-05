#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import time
import json
import dbus

from pybot.minitel import Minitel
from pybot.minitel.menu import Menu
from pybot.minitel import constants

from pybot.youpi import YoupiArduinoInterface, YoupiArmController

from pybot.dynamixel.dmxl_bus_intf import USB2AX
from pybot.dynamixel.gestures import GestureController, Gesture
from pybot.dynamixel.joints import logger as joints_logger

from nros.core.node import DEFAULT_SERVICE_OBJECT_PATH

AX12_ARM = False

__author__ = 'Eric Pascual'

__all__ = ['Application']


class DummyLogger(object):
    def _noop(self, *args, **kwargs):
        pass

    info = warning = error = debug = setLevel = _noop


class Application(object):
    """ The application object.
    """

    pose_home = {
        "shoulder": 260,
        "elbow": 15,
        "base": 240,
        "wrist": 55,
        "gripper": 150
    }

    def __init__(self, minitel_port=None,
                 arm_port=None, arm_busname=None,
                 config_file=None, log=None, debug=False):
        self._log = log or DummyLogger()

        self._mt = None
        self._arm = None

        self._debug = debug
        self._log.setLevel(logging.DEBUG if debug else logging.INFO)
        self._log.info('current logging level : %s', logging.getLevelName(self._log.getEffectiveLevel()))
        joints_logger.setLevel(self._log.getEffectiveLevel())

        self._log.info('args:')
        self._log.info('- minitel_port=%s', minitel_port)
        self._log.info('- arm_port=%s', arm_port)
        self._log.info('- arm_busname=%s', arm_busname)
        self._log.info('- config_file=%s', config_file)

        self._demos = [
            (m.__doc__, m) for m in (getattr(self, name)for name in sorted(dir(self)) if name.startswith('demo_'))
        ]

        try:
            cfg = json.load(config_file)
        except ValueError as e:
            raise ValueError('invalid configuration data : %s' % e)

        cfg_minitel = cfg['minitel']
        minitel_port = minitel_port or cfg_minitel['port']
        if os.path.exists(minitel_port):
            self._minitel_port = minitel_port
        else:
            raise ValueError('port not found : %s' % minitel_port)

        self._arm_port = self._arm_busname = None

        self._cfg_arm = cfg["arm"]
        arm_port = arm_port or self._cfg_arm.get("port", None)
        arm_busname = arm_busname or self._cfg_arm.get("busname", None)

        if arm_port:
            if os.path.exists(arm_port):
                self._arm_port = arm_port
                self._arm_baudrate = self._cfg_arm.get("baudrate", 1000000)
            else:
                raise ValueError('port not found : %s' % arm_port)

        elif arm_busname:
            self._arm_busname = arm_busname

        else:
            raise ValueError('at least on of arm_port or arm_busname must be provided')

    def run(self):
        """ Application run mainline
        """
        self._log.info('creating Minitel instance on %s', self._minitel_port)
        self._mt = Minitel(self._minitel_port)  # , debug=self._debug)
        self._mt.clear_all()
        self._mt.display_status(
            self._mt.text_style_sequence(inverse=True) +
            u'Démonstration YouPinitel'.ljust(self._mt.get_screen_width())
        )

        if self._arm_port:
            arm_type = 'AX12' if AX12_ARM else 'Youpi'
            if not AX12_ARM:
                self._arm_baudrate = 9600
            self._log.info('creating %s arm interface instance on %s (baudrate=%d)',
                           arm_type, self._arm_port, self._arm_baudrate)
            if AX12_ARM:
                intf = USB2AX(self._arm_port, baudrate=self._arm_baudrate)
                self._arm = GestureController(intf)
                self._arm.configure_joints(self._cfg_arm['joints'])
            else:
                self._log.info('initializing Youpi interface and arm')
                self._mt.display_text_center("Initialisation du bras", y=5)
                self._mt.display_text_center(u"Veuillez patienter...", y=7)
                intf = YoupiArduinoInterface(self._arm_port)
                intf.wait_for_ready()

                self._mt.clear_screen()

                self._arm = YoupiArmController(intf)
                # self._arm.base.set_goal_angle(150)
                # while math.fabs(self._arm.base.get_current_angle() - 150) >= 1:
                #     time.sleep(0.1)
                self.pose_home = dict(self._arm.get_pose())
                self._log.info('Youpi home pose:')
                for n, a in self.pose_home.iteritems():
                    self._log.info('- %-10s : %5.1f', n, a)

        elif self._arm_busname:
            self._log.info("connecting to arm nROS controller '%s'", self._arm_busname)
            bus = dbus.SessionBus()
            self._arm = bus.get_object(self._arm_busname, DEFAULT_SERVICE_OBJECT_PATH)
            self._arm.joints = dict([
                (n, bus.get_object(self._arm_busname, '/joint/%s' % n)) for n in self._arm.get_joint_names()
            ])

        else:
            raise Exception('no arm controller connection was configured')

        title = 'Menu principal'

        while True:
            self._log.info('displaying main menu')
            menu = Menu(
                self._mt,
                title=[title, '-' * len(title)],
                choices=[t[0] for t in self._demos],
                prompt='Votre choix',
                line_skip=2,
                margin_top=1,
                prompt_line=20,
                addit=[(0, 23, ' SOMMAIRE: fin '.center(40, '-'))]
            )

            choice = menu.get_choice()

            if choice:
                label, method = self._demos[choice - 1]
                self._log.info('selected demo : %s', label)
                method()
            else:
                break

        self._mt.clear_all()
        self._mt.display_text(u"Damien & Eric vous disent à bientôt.")

    def _move_arm_home(self):
        self._log.info('moving arm to its home position...')
        if AX12_ARM:
            gesture = Gesture([(self.pose_home, 2)])
            data = gesture.as_json() if self._arm_busname else gesture
            self._arm.execute_gesture(data)
        else:
            # for j, a in self.pose_home.iteritems():
            #     self._log.info("- %-10s -> %5.1f", j, a)
            #     self._arm.joints[j].set_goal_angle(a)
            self._arm.reset()

    def demo_00_infos(self):
        u"""quelques explications"""

        self._mt.clear_screen()
        for l, text in enumerate([
            u'La rencontre des années 80:',
            u'',
            u"Youpi: ",
            u"   Un bras robotique pour l'enseignement",
            "",
            u"Le Minitel: ",
            u"   L'ancêtre d'Internet",
            u'',
            u'... et du 21ème siècle:',
            u'',
            u"L'Arduino: ",
            u"   Une carte pour l'initiation à la ",
            u"   programmation des micro-contrôleurs",
            '',
            u"La RaspberryPi: ",
            u"   Un ordinateur de la taille d'une ",
            u"   carte de crédit"
        ]):
            self._mt.display_text(text=text, x=0, y=l + 2)

        self._mt.display_text_center(u'Retour : menu principal', y=23)
        self._mt.wait_for_key([constants.SEP + constants.KeyCode.RETOUR], max_wait=300)

    def _demo_01(self):
        u"""dis bonjour avec le bras"""
        self._mt.display_text_center(' je vous dis bonjour ', 23, pad_char='-')
        pose_extended = {
            "shoulder": 170,    # 82,
            "elbow": 60,        # 73,
            "base": 240,
            "wrist": 202,
            "gripper": 150
        }
        pose_to_the_right = {
            "base": 200
        }
        pose_to_the_left = {
            "base": 280
        }

        gesture = Gesture([
            (pose_extended, 1),
            (None, 0.5),
            (pose_to_the_right, 0.5),
            (pose_to_the_left, 1),
            (pose_extended, 0.5),
            (None, 1),
            (self.pose_home, 2)
        ])
        data = gesture.as_json() if self._arm_busname else gesture
        self._arm.execute_gesture(data)

    def _demo_02(self):
        u"""déplace le Rubik's cube"""
        self._mt.display_text_center(' moving the cube ', 23, pad_char='-')
        time.sleep(3)

    def demo_03(self):
        u"""contrôle manuel"""

        base = self._arm.joints['base']
        shoulder = self._arm.joints['shoulder']
        elbow = self._arm.joints['elbow']
        wrist = self._arm.joints['wrist']
        gripper = self._arm.joints['gripper']
        wrist_rot = None if AX12_ARM else self._arm.joints['wrist_rot']

        speed = 10 if AX12_ARM else None

        def _move_joint(joint, step):
            goal_pos = joint.get_current_angle() + step
            self._log.info('moving joint %s from angle %5.1f to angle %5.1f', joint.servo_id, joint.get_current_angle(), goal_pos)
            joint.set_goal_angle(goal_pos, speed, immediate=True, wait=False)

        def shoulder_up():
            _move_joint(shoulder, 5)

        def shoulder_down():
            _move_joint(shoulder, -5)

        def elbow_up():
            _move_joint(elbow, +5 * (1 if AX12_ARM else -1))

        def elbow_down():
            _move_joint(elbow, -5 * (1 if AX12_ARM else -1))

        def wrist_up():
            _move_joint(wrist, +5)

        def wrist_down():
            _move_joint(wrist, -5)

        def base_left():
            _move_joint(base, 5)

        def base_right():
            _move_joint(base, -5)

        def gripper_open():
            if hasattr(self._arm, 'open_gripper'):
                self._arm.open_gripper()
            else:
                gripper.set_goal_angle(100, 0, immediate=True, wait=False)

        def gripper_close():
            if hasattr(self._arm, 'close_gripper'):
                self._arm.close_gripper()
            else:
                gripper.set_goal_angle(150, 0, immediate=True, wait=False)

        def wrist_ccw():
            _move_joint(wrist_rot, -5)

        def wrist_cw():
            _move_joint(wrist_rot, 5)

        actions = {
            '1': shoulder_up,
            '4': shoulder_down,
            '2': elbow_up,
            '5': elbow_down,
            '3': wrist_up,
            '6': wrist_down,
            '7': base_left,
            '9': base_right,
            'O': gripper_open,
            'F': gripper_close,
            '*': wrist_ccw,
            '#': wrist_cw,
            'R': self._move_arm_home,
        }

        self._mt.clear_screen()
        for l, text in enumerate([
            u'Utilisez les touches du clavier',
            u'pour contrôler le bras.',
            '',
            u'1 4 : épaule',
            u'2 5 : coude',
            u'3 6 : poignet',
            u'7 9 : rotation bras',
            u'* # : rotation pince',
            u'O F : ouverture/fermeture pince',
            '',
            u' R  : retour position initiale'
        ]):
            self._mt.display_text(text=text, x=0, y=l + 4)

        self._mt.display_text_center(u'Retour : menu principal', y=23)

        key_return = constants.SEP + constants.KeyCode.RETOUR
        valid_keys = actions.keys() + [key_return]
        while True:
            key = self._mt.wait_for_key(valid_keys, max_wait=60)
            if key in (None, key_return):
                if not key:
                    self._log.info('no input => return to main menu')
                self._mt.clear_screen()
                self._mt.display_text_center(u"Réinitialisation du bras", y=5)
                self._mt.display_text_center(u"Veuillez patienter...", y=7)
                self._move_arm_home()
                return
            else:
                try:
                    actions[key]()
                except KeyError:
                    self._mt.beep()
