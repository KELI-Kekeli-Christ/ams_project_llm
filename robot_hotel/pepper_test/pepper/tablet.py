#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tablet display module for pepper_test.
Handles tablet display functionality for the Pepper robot.
"""

import time


def display_tablet_content(robot, html_content, delay=1.0):
    """
    A generic function to display content on the tablet.
    
    Args:
        robot: RobotManager instance
        html_content: HTML content to display
        delay: Delay after displaying (default 1.0s)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not robot.tablet:
        print("Service Tablet non disponible")
        return False
    
    result = robot.display_text(html_content)
    if result and delay > 0:
        time.sleep(delay)
    return result


def show_greeting(robot, name=None):
    """
    Show greeting message on tablet.
    
    Args:
        robot: RobotManager instance
        name: Name of the person (optional)
    
    Returns:
        bool: True if successful
    """
    from ui.tablet_html import create_tablet_html
    
    greeting_text = "Ah bonjour {} !".format(name) if name else "Prêt à vous aider"
    html_content = create_tablet_html(
        title="Pepper",
        message=greeting_text,
        subtitle="",
        status="En attente",
        show_mic_button=True,
        mic_active=False,
        robot_ip=robot.ip
    )
    return display_tablet_content(robot, html_content)


def show_recording(robot, active=True, robot_ip=None):
    """
    Show recording interface on tablet.
    
    Args:
        robot: RobotManager instance
        active: Whether recording is active
        robot_ip: IP of the robot
    
    Returns:
        bool: True if successful
    """
    from ui.tablet_html import create_tablet_html
    
    title = "Enregistrement..." if active else "Pret"
    message = "Je vous ecoute" if active else "Cliquez sur le micro pour parler"
    status = "Enregistrement en cours..." if active else "En attente..."
    
    html_content = create_tablet_html(
        title=title,
        message=message,
        status=status,
        show_mic_button=True,
        mic_active=active,
        robot_ip=robot_ip or robot.ip
    )
    return display_tablet_content(robot, html_content)


def show_processing(robot, message="Traitement en cours..."):
    """
    Show processing message on tablet.
    
    Args:
        robot: RobotManager instance
        message: Message to display
    
    Returns:
        bool: True if successful
    """
    from ui.tablet_html import create_tablet_html
    
    html_content = create_tablet_html(
        title="Traitement...",
        message=message,
        status="Analyse en cours...",
        show_mic_button=False
    )
    return display_tablet_content(robot, html_content)


def show_result(robot, title, message, subtitle="", status="", show_mic=True):
    """
    Show result message on tablet.
    
    Args:
        robot: RobotManager instance
        title: Title to display
        message: Main message
        subtitle: Subtitle (optional)
        status: Status text (optional)
        show_mic: Whether to show microphone button
    
    Returns:
        bool: True if successful
    """
    from ui.tablet_html import create_tablet_html
    
    html_content = create_tablet_html(
        title=title,
        message=message,
        subtitle=subtitle,
        status=status,
        show_mic_button=show_mic,
        mic_active=False,
        robot_ip=robot.ip
    )
    return display_tablet_content(robot, html_content)


def show_error(robot, error_message, subtitle=""):
    """
    Show error message on tablet.
    
    Args:
        robot: RobotManager instance
        error_message: Error message to display
        subtitle: Additional details (optional)
    
    Returns:
        bool: True if successful
    """
    return show_result(
        robot,
        title="Erreur",
        message=error_message,
        subtitle=subtitle,
        status="Erreur",
        show_mic=True
    )


def show_success(robot, message, details=""):
    """
    Show success message on tablet.
    
    Args:
        robot: RobotManager instance
        message: Success message to display
        details: Additional details (optional)
    
    Returns:
        bool: True if successful
    """
    return show_result(
        robot,
        title="Succes",
        message=message,
        subtitle=details,
        status="Termine",
        show_mic=True
    )


def show_farewell(robot):
    """
    Show farewell message on tablet.
    
    Args:
        robot: RobotManager instance
    
    Returns:
        bool: True if successful
    """
    from ui.tablet_html import create_tablet_html
    
    html_content = create_tablet_html(
        title="Au revoir",
        message="Merci pour votre visite",
        status="Conversation terminee",
        show_mic_button=False
    )
    return display_tablet_content(robot, html_content)


def show_chat_interface(robot):
    """
    Show chat interface on tablet.
    Displays a button to open the full chat interface.
    
    Args:
        robot: RobotManager instance
    
    Returns:
        bool: True if successful
    """
    from ui.tablet_html import create_tablet_html
    
    html_content = create_tablet_html(
        title="Pepper",
        message="Discutez avec moi !",
        subtitle="Cliquez sur le bouton ci-dessous pour ouvrir le chat",
        status="En ligne",
        show_mic_button=True,
        mic_active=False,
        show_chat_button=True,
        robot_ip=robot.ip
    )
    return display_tablet_content(robot, html_content)

