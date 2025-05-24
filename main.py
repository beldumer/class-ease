API_BASE = "http://192.168.1.8:5000"

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.lang import Builder
from kivy.uix.modalview import ModalView
from kivy.factory import Factory
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import get_color_from_hex
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.properties import StringProperty
from kivy.uix.image import Image
# from kivy.core.image import Image as CoreImage
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.filechooser import FileChooserListView
from datetime import datetime
from os.path import expanduser
# from pdf2image import convert_from_path
import requests
from requests.exceptions import RequestException
import webbrowser
import time
import json
import io
import threading
# from tkinter import Tk, filedialog

# DRY logic, helper function for days of the week
def update_schedule_common(container, subjects):
    container.clear_widgets()
    for subject in subjects:
        subject_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(120),
            padding=dp(10),
            spacing=dp(5)
        )

        with subject_box.canvas.before:
            Color(*get_color_from_hex('#faf9f6'))
            rect = RoundedRectangle(
                pos=subject_box.pos,
                size=subject_box.size,
                radius=[dp(10)]
            )
        subject_box.bind(
            pos=lambda instance, value, rect=rect: setattr(rect, 'pos', value),
            size=lambda instance, value, rect=rect: setattr(rect, 'size', value)
        )

        subject_box.add_widget(Label(
            text=f"[b]Course:[/b] {subject['course_name']}",
            font_size='16sp',
            markup=True,
            bold=True,
            color=get_color_from_hex('#000000'),
            size_hint_y=None,
            height=dp(20)
        ))
        subject_box.add_widget(Label(
            text=f"[b]Time:[/b] {subject['start_time']} - {subject['end_time']}",
            font_size='14sp',
            markup=True,
            color=get_color_from_hex('#000000'),
            size_hint_y=None,
            height=dp(20)
        ))
        subject_box.add_widget(Label(
            text=f"[b]Professor:[/b] {subject['professor_name']}",
            font_size='14sp',
            markup=True,
            color=get_color_from_hex('#000000'),
            size_hint_y=None,
            height=dp(20)
        ))
        subject_box.add_widget(Label(
            text=f"[b]Classroom:[/b] {subject['classroom_name']}",
            font_size='14sp',
            markup=True,
            color=get_color_from_hex('#000000'),
            size_hint_y=None,
            height=dp(20)
        ))

        container.add_widget(subject_box)


def show_quick_popup(message, duration=1.5):
    class RoundedPopup(Popup):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            with self.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(rgba=get_color_from_hex('#e6f0fa'))  # baby blue
                self.bg_rect = RoundedRectangle(
                    pos=self.pos,
                    size=self.size,
                    radius=[20]
                )
            self.bind(pos=self.update_bg, size=self.update_bg)

        def update_bg(self, *args):
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size

    popup = RoundedPopup(
        title='',
        content=Label(
            text=message,
            font_size='16sp',
            color=get_color_from_hex('#111344'),
            halign='center',
            valign='middle'
        ),
        size_hint=(None, None),
        size=(320, 110),
        auto_dismiss=True,
        separator_height=0,
        background='' 
    )
    popup.open()
    Clock.schedule_once(lambda dt: popup.dismiss(), duration)


def show_notification_popup(notif):
    content = BoxLayout(orientation='vertical', padding=15, spacing=10)
    content.add_widget(Label(
        text=f"[b]{notif.get('title', '')}",
        markup=True, bold=True, font_size='20sp', color=get_color_from_hex('#111344'),
        size_hint_y=None, height=dp(30)
    ))
    scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
    msg_label = Label(
        text=notif.get('message', ''),
        font_size='16sp',
        color=get_color_from_hex('#000000'),
        size_hint_y=None,
        text_size=(dp(350), None),
        halign='left',
        valign='top',
        markup=True
    )
    msg_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1]))
    scroll.add_widget(msg_label)
    content.add_widget(scroll)
    content.add_widget(Label(
        text=f"[i]{notif.get('date', '')}[/i]",
        markup=True,
        font_size='12sp',
        color=get_color_from_hex('#808080'),
        size_hint_y=None,
        height=dp(20)
    ))
    popup = Popup(
        title='Notification',
        content=content,
        size_hint=(None, None),
        size=(400, 350),
        auto_dismiss=True,
        background='atlas://data/images/defaulttheme/button_pressed',  # Rounded background
    )
    popup.open()


class NotificationButton(ButtonBehavior, BoxLayout):
    def __init__(self, notif, **kwargs):
        super().__init__(orientation='vertical', padding=dp(10), spacing=dp(5), **kwargs)
        self.notif = notif
        with self.canvas.before:
            Color(*get_color_from_hex('#e6f0fa'))
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self.update_rect, size=self.update_rect)
        self.add_widget(Label(
            text=f"[b]{notif.get('course_name', '')}[/b] - {notif.get('title', '')}",
            markup=True, font_size='16sp', color=get_color_from_hex('#111344'),
            size_hint_y=None, height=dp(24)
        ))
        # Preview message (first 60 chars)
        msg = notif.get('message', '')
        preview = msg[:60] + ('...' if len(msg) > 60 else '')
        self.add_widget(Label(
            text=preview, font_size='14sp', color=get_color_from_hex('#000000'),
            size_hint_y=None, height=dp(24)
        ))
        self.add_widget(Label(
            text=f"[i]{notif.get('date', '')}[/i]", markup=True,
            font_size='12sp', color=get_color_from_hex('#808080'),
            size_hint_y=None, height=dp(18)
        ))

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_press(self):
        show_notification_popup(self.notif)


class WelcomeScreen(Screen): pass
class LoginScreen(Screen): pass
class StudentOverlay(ModalView):
    def login(self):
        URL = f"{API_BASE}/login"
        username = self.ids.student_username.text.strip()
        password = self.ids.student_password.text.strip()

        # Validate input
        if not username or not password:
            self.ids.student_error.text = "Please enter both username and password."
            return
        if len(username) < 3 or len(password) < 6:
            self.ids.student_error.text = "Username must be at least 3 characters and password at least 6 characters."
            return

        # Disable the login button and show a loading message
        self.ids.login_button.disabled = True
        self.ids.student_error.text = "Logging in..."

        try:
            retries = 3
            for attempt in range(retries):
                try:
                    response = requests.post(URL, json={
                        "login_name": username,
                        "password": password
                    }, timeout=10)

                    print(f"Response Status Code: {response.status_code}")
                    resp_json = response.json()
                    print(f"Response Content: {resp_json}")

                    if response.status_code == 200:
                        app = App.get_running_app()
                        app.student_id = resp_json.get("id")
                        courses = resp_json.get("courses", [])
                        app.student_courses = courses
                        app.student_subjects = [c["course_name"] for c in courses]

                        # Create SubjectNotesScreen for each subject
                        sm = app.root
                        for subject in app.student_subjects:
                            screen_name = f"subject_{subject.replace(' ', '_')}"
                            if not sm.has_screen(screen_name):
                                sm.add_widget(SubjectNotesScreen(name=screen_name, subject_name=subject))

                        self.ids.student_error.text = "Login successful!"
                        app.root.current = 'mainsc'
                        self.dismiss()
                        return
                    elif response.status_code == 401:
                        self.ids.student_error.text = "Invalid credentials. Please try again."
                        return
                    else:
                        self.ids.student_error.text = "An unexpected error occurred. Please try again later."
                        return
                except requests.exceptions.RequestException as e:
                    if attempt < retries - 1:
                        time.sleep(2)
                        continue
                    self.ids.student_error.text = f"Error: {str(e)}"
                    return
        finally:
            self.ids.login_button.disabled = False
class TeacherOverlay(ModalView):
    def login(self):
        username = self.ids.teacher_username.text
        password = self.ids.teacher_password.text

        try:
            response = requests.post(f"{API_BASE}/login", json={
                "login_name": username,
                "password": password
            }, timeout=10)
            print("Teacher login response:", response.status_code, response.text)
            if response.status_code == 200:
                courses = response.json().get("courses", [])
                print("Courses from server:", courses)
                app = App.get_running_app()
                app.teacher_id = response.json().get("id")
                app.teacher_subject_dict = {c["name"]: c["id"] for c in courses}
                app.root.current = 'mainsc2'
                self.dismiss()
            else:
                self.ids.teacher_error.text = "Invalid credentials. Please try again."
        except requests.exceptions.RequestException as e:
            self.ids.teacher_error.text = f"Network error: {e}"
class MainScreen(Screen):
    def on_enter(self):
        notifications = App.get_running_app().fetch_notifications(
            student_id=App.get_running_app().student_id, limit=5
        )
        container = self.ids.main_notifications_container
        container.clear_widgets()
        for notif in notifications:
            btn = NotificationButton(notif, size_hint_y=None, height=dp(80))
            container.add_widget(btn)
class MenuOverlay(ModalView): 
    def on_open(self):
        self.opacity = 1
        self.pos_hint = {"center_x": -0.7, "center_y": -0.5}
        
        anim= Animation(pos_hint = {"center_x": 0.5, "center_y": 0.5}, duration = 0.7, t = 'in_out_quint')
        anim.start(self)
class MenuOverlay2(ModalView): 
    def on_open(self):
        self.opacity = 1
        self.pos_hint = {"center_x": -0.7, "center_y": -0.5}
        
        anim= Animation(pos_hint = {"center_x": 0.5, "center_y": 0.5}, duration = 0.7, t = 'in_out_quint')
        anim.start(self)
class MapScreen(Screen):
    active_button = None

    def set_active_button(self, button):
        if self.active_button:
            self.active_button.canvas.before.clear()
            with self.active_button.canvas.before:
                Color(rgba=(0, 0, 0, 0.3))
                RoundedRectangle(
                    pos=(self.active_button.x + dp(5), self.active_button.y - dp(5)),
                    size=self.active_button.size,
                    radius=[dp(25)]
                )

                Color(rgba=get_color_from_hex('#111344'))
                RoundedRectangle(
                    pos=self.active_button.pos,
                    size=self.active_button.size,
                    radius=[dp(20)]
                )

        self.active_button = button
        button.canvas.before.clear()
        with button.canvas.before:
            Color(rgba=(0, 0, 0, 0.3))
            RoundedRectangle(
                pos=(button.x + dp(5), button.y - dp(5)),
                size=button.size,
                radius=[dp(25)]
            )

            Color(rgba=(0.34, 0.34, 0.34, 1))
            RoundedRectangle(
                pos=button.pos,
                size=button.size,
                radius=[dp(20)]
            )
class Timetable(Screen):
    def schedule(self, day):
        student_id= App.get_running_app().student_id
        url = f"{API_BASE}/schedule"

        if not student_id:
            print("Error: Student ID is not available.")
            return

        try:
            response = requests.post(
                url,
                json={
                    "id": student_id,
                    "day_name": day
                }
            )

            if response.status_code == 200:
                print(f"Response JSON: {response.json()}")

                full_schedule = response.json().get("schedule", {})
                #print(f"Full Schedule: {full_schedule}")

                if isinstance(full_schedule, str):
                    try:
                        full_schedule = json.loads(full_schedule)
                        #print(f"Parsed Full Schedule: {full_schedule}")
                    except json.JSONDecodeError:
                        print(f"Failed to parse schedule string: {full_schedule}")
                        return
                    
                subjects = set(subjects['course_name'] for subjects in full_schedule)
                
                sm = self.manager
                for subject in subjects:
                    screen_name = f"subject_{subject.replace(' ', '_')}"
                    if not sm.has_screen(screen_name):
                        sm.add_widget(SubjectNotesScreen(name=screen_name, subject_name=subject))

                # Group subjects by day_name
                grouped_schedule = {}
                for subject in full_schedule:
                    day_name = subject.get("day_name")
                    if day_name not in grouped_schedule:
                        grouped_schedule[day_name] = []
                    grouped_schedule[day_name].append(subject)

                #print(f"Grouped Schedule: {grouped_schedule}")  # Debugging

                # Handle grouped schedule
                screen_map = {
                    "Δευτερα": "Smonday",
                    "Τρίτη": "Stuesday",
                    "Τετάρτη": "Swednesday",
                    "Πέμπτη": "Sthursday",
                    "Παρασκευή": "Sfriday"
                }

                # Update the appropriate screen with the subjects
                for greek_day, subjects in grouped_schedule.items():
                    screen_name = screen_map.get(greek_day)
                    if screen_name and self.manager.has_screen(screen_name):
                        screen = self.manager.get_screen(screen_name)
                        screen.update_schedule(subjects)

                # Switch to the selected day's screen
                if day in screen_map:
                    App.get_running_app().root.current = screen_map[day]
                else:
                    print(f"No screen found for {day}")
            else:
                print(f"Server error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")
class MondayScreen(Screen):
    def update_schedule(self, subjects):
        print(f"Updating Monday schedule with subjects: {subjects}")
        container = self.ids.subject_container
        update_schedule_common(container, subjects)
class TuesdayScreen(Screen):
    def update_schedule(self, subjects):
        print(f"Updating Tuesday schedule with subjects: {subjects}")
        container = self.ids.subject_container
        update_schedule_common(container, subjects)
class WednesdayScreen(Screen):
    def update_schedule(self, subjects):
        print(f"Updating Wednesday schedule with subjects: {subjects}")
        container = self.ids.subject_container
        update_schedule_common(container, subjects)
class ThursdayScreen(Screen):
    def update_schedule(self, subjects):
        print(f"Updating Thursday schedule with subjects: {subjects}")
        container = self.ids.subject_container
        update_schedule_common(container, subjects)
class FridayScreen(Screen):
    def update_schedule(self, subjects):
        print(f"Updating Friday schedule with subjects: {subjects}")
        container = self.ids.subject_container
        update_schedule_common(container, subjects)
class Statistics(Screen): pass
class SubjectNotesScreen(Screen):
    subject_name = StringProperty("")

    def __init__(self, subject_name, **kwargs):
        super().__init__(**kwargs)
        self.subject_name = subject_name
        self.refresh_events = None

    def on_pre_enter(self):
        self.refresh_events = Clock.schedule_interval(lambda dt: self.fetch_notes(), 10)

    def on_leave(self):
        if self.refresh_events:
            self.refresh_events.cancel()
            self.refresh_events = None

    def fetch_notes(self):
        # Find course_id for this subject
        course_id = None
        for course in getattr(App.get_running_app(), "student_courses", []):
            if course["course_name"] == self.subject_name:
                course_id = course["course_id"]
                break
        if not course_id:
            print("No course_id found for subject:", self.subject_name)
            return

        url = f"{API_BASE}/view_notes"
        try:
            response = requests.post(url, json={"course_id": course_id}, timeout=10)
            if response.status_code == 200:
                notes = response.json().get("notes", [])
                self.update_notes(notes)
            else:
                print("Failed to fetch notes: ", response.status_code, response.text)
        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")

    def update_notes(self, notes):
        container = self.ids.subject_notes_container
        container.clear_widgets()
        for note in notes:
            note_box = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(120),
                padding=dp(10),
                spacing=dp(5)
            )
            with note_box.canvas.before:
                Color(*get_color_from_hex('#faf9f6'))
                rect = RoundedRectangle(
                    pos=note_box.pos,
                    size=note_box.size,
                    radius=[dp(10)]
                )
            note_box.bind(
                pos=lambda instance, value, rect=rect: setattr(rect, 'pos', value),
                size=lambda instance, value, rect=rect: setattr(rect, 'size', value)
            )
            filename = note.get('filename', 'No file')
            username = note.get('username', '')
            url = note.get('url', '')
            date = note.get('date', '')
            size = note.get('size', '')
            try:
                size_str = f"{int(float(size))} KB" if size else "Unknown"
            except ValueError:
                size_str = "Unknown"

            # Filename (bold, centered)
            note_box.add_widget(Label(
                text=f"[b]{filename}[/b]",
                font_size='16sp',
                markup=True,
                bold=True,
                color=get_color_from_hex('#000080'),
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(24)
            ))
            note_box.add_widget(Label(
                text=f"By: {username}   |   Date: {date}   |   Size: {size_str}",
                font_size='12sp',
                markup=True,
                bold=True,
                color=get_color_from_hex('#808080'),
                halign='center',
                valign='middle',
                size_hint_y=None,
                height=dp(20)
            ))
            # Download button
            if url:
                btn = Button(
                    text="Download PDF",
                    size_hint_y=None,
                    height=dp(30),
                    background_normal='',
                    background_color=get_color_from_hex('#000080'),
                    color=get_color_from_hex('#faf9f6'),
                    on_press=lambda instance, url=url, filename=filename: self.download_pdf(url, filename)
                )
                note_box.add_widget(btn)
            container.add_widget(note_box)
            
    def download_pdf(self, url, filename):
        def do_download():
            save_path = expanduser(f"~/Download/{filename}")

            if not save_path:
                return
            try:
                response = requests.get(url, stream=True, timeout=20)
                response.raise_for_status()
                with open(save_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"Downloaded to {save_path}")
            except Exception as e:
                print(f"Download failed: {e}")

        threading.Thread(target=do_download).start()

    def upload_note(self):
        popup = UploadNotePopup(subject_name=self.subject_name)
        popup.open()
class Notes(Screen):
    def on_enter(self):
        self.show_subject_list()

    def show_subject_list(self):
        subjects = getattr(App.get_running_app(), "student_subjects", [])
        container = self.ids.subject_list_container
        container.clear_widgets()
        for subject in subjects:
            btn = Button(
                text=subject,
                size_hint_y=None,
                height=dp(50),
                background_normal='',
                background_color=(0, 0, 0, 0),
                color=get_color_from_hex('#000000'),
                on_press=lambda instance, s=subject: self.open_subject_notes(s)
            )
            # Add rounded corners using canvas.before
            with btn.canvas.before:
                Color(rgba=get_color_from_hex('#faf9f6'))
                rect = RoundedRectangle(
                    pos=btn.pos,
                    size=btn.size,
                    radius=[dp(20)]
                )
                
            def update_rect(instance, value, rect=rect):
                rect.pos = instance.pos
                rect.size = instance.size
                
            btn.bind(pos=update_rect, size=update_rect)
            container.add_widget(btn)

    def open_subject_notes(self, subject):
        screen_name = f"subject_{subject.replace(' ', '_')}"
        if self.manager.has_screen(screen_name):
            self.manager.current = screen_name
class MainScreen2(Screen): pass
class TeacherUploadScreen(Screen):
    def on_pre_enter(self):
        app = App.get_running_app()
        subjects_dict = getattr(app, "teacher_subject_dict", {})
        self.subjects_dict = subjects_dict

        spinner = self.ids.subject_spinner
        spinner.values = list(subjects_dict.keys())
        if spinner.values:
            spinner.text = "Select Course"
        else:
            spinner.text = "No subjects"

    def send_notification(self):
        title = self.ids.message_title.text.strip()
        message = self.ids.message_body.text.strip()
        subject_name = self.ids.subject_spinner.text.strip()
        teacher_id = App.get_running_app().teacher_id

        # Get subject_id from the selected subject name
        subject_id = self.subjects_dict.get(subject_name)

        if not title or not message or not subject_id:
            print("All fields are required.")
            return

        # Get current date and time
        now = datetime.now()
        date_hour = now.strftime("%Y-%m-%d %H:%M:%S")

        data = {
            "course_id": subject_id,
            "title": title,
            "message": message
        }
        try:
            response = requests.post(f"{API_BASE}/send_notification", json=data, timeout=10)
            if response.status_code == 200:
                print("Notification sent successfully!")
                self.ids.message_title.text = ""
                self.ids.message_body.text = ""
                # Reset spinner to first value if available
                if self.ids.subject_spinner.values:
                    self.ids.subject_spinner.text = self.ids.subject_spinner.values[0]
                else:
                    self.ids.subject_spinner.text = "No subjects"
                show_quick_popup("Notification sent successfully!")
            else:
                print("Failed to send notification.")
        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")
class UploadNotePopup(Popup):
    def __init__(self, subject_name, **kwargs):
        super().__init__(**kwargs)
        self.title = f"Upload Note for {subject_name}"
        self.size_hint = (0.9, 0.6)
        self.auto_dismiss = True
        self.subject_name = subject_name
        self.selected_pdf = None
        
        self.background= ''
        self.background_color = get_color_from_hex('#000000')

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # self.title_input = TextInput(hint_text="Note Title", multiline=False)
        self.file_btn = Button(text="Choose PDF", size_hint_y=None, height=dp(20))
        self.file_btn.bind(on_press=self.open_file_dialog)
        self.selected_file_label = Label(text="No file selected", size_hint_y=None, height=dp(20), font_size='12sp')
        # self.preview_image = Image(size_hint_y=None , height=dp(200))
        submit_btn = Button(text="Upload", size_hint_y=None, height=dp(40))
        submit_btn.bind(on_press=self.upload)

        # layout.add_widget(self.title_input)
        layout.add_widget(self.file_btn)
        layout.add_widget(self.selected_file_label)
        # layout.add_widget(self.preview_image)
        layout.add_widget(submit_btn)

        self.add_widget(layout)

    def open_file_dialog(self, *args):
        content = BoxLayout(orientation='vertical', spacing=10)
        filechooser = FileChooserListView(filters=["*.pdf"])
        content.add_widget(filechooser)

        def on_select(*_):
            selection = filechooser.selection
            if selection:
                self.selected_pdf = selection[0]
                self.selected_file_label.text = f"Selected: {self.selected_pdf.split('/')[-1]}"
                popup.dismiss()

        select_btn = Button(text="Select", size_hint_y=None, height=dp(40))
        select_btn.bind(on_release=on_select)
        content.add_widget(select_btn)

        popup = Popup(
            title="Select a PDF",
            content=content,
            size_hint=(0.9, 0.9),
            auto_dismiss=True
        )
        popup.open()

    '''        
    def show_pdf_preview(self, pdf_path):
        try:
            # Convert first page of PDF to image
            images = convert_from_path(pdf_path, first_page=1, last_page=1, fmt='png')
            print("Image from pdf:", images)
            if images:
                buf = io.BytesIO()
                images[0].save(buf, format='PNG')
                buf.seek(0)
                core_img = CoreImage(buf, ext='png')
                self.preview_image.texture = core_img.texture
            else:
                print("No images found in PDF.")
        except Exception as e:
            print(f"Failed to preview PDF: {e}")
            self.preview_image.texture = None
    '''

    def upload(self, *args):
        student_id = App.get_running_app().student_id
        # Find course_id for this subject
        course_id = None
        for course in getattr(App.get_running_app(), "student_courses", []):
            if course["course_name"] == self.subject_name:
                course_id = course["course_id"]
                break

        if not student_id or not course_id or not self.selected_pdf:
            print("All fields and PDF file are required.")
            return

        url = f"{API_BASE}/upload"
        file = {'file': open(self.selected_pdf, 'rb')}
        data = {
            "student_id": str(student_id),
            "course_id": str(course_id)
        }

        try:
            response = requests.post(url = url , data=data, files=file, timeout=10)
            if response.status_code == 200:
                print("Note uploaded successfully.")
                show_quick_popup("Note uploaded successfully!")
                self.dismiss()
            else:
                print("Failed to upload note.")
        except requests.exceptions.RequestException as e:
            print(f"Upload failed: {str(e)}")
        finally:
            file['file'].close()
class TeacherSchedule(Screen):
    def on_enter(self):
        teacher_id = App.get_running_app().teacher_id
        url = f"{API_BASE}/prof_schedule"
        try:
            response = requests.post(url, json={"id": teacher_id}, timeout=10)
            if response.status_code == 200:
                schedule = response.json().get("schedule", [])
                self.update_schedule(schedule)
            else:
                print("Failed to fetch teacher schedule.")
        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")

    def update_schedule(self, schedule):
        container = self.ids.teacher_schedule_container
        container.clear_widgets()
        for subject in schedule:
            subject_box = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(120),
                padding=dp(10),
                spacing=dp(5)
            )
            with subject_box.canvas.before:
                Color(*get_color_from_hex('#faf9f6'))
                rect = RoundedRectangle(
                    pos=subject_box.pos,
                    size=subject_box.size,
                    radius=[dp(10)]
                )
            subject_box.bind(
                pos=lambda instance, value, rect=rect: setattr(rect, 'pos', value),
                size=lambda instance, value, rect=rect: setattr(rect, 'size', value)
            )
            subject_box.add_widget(Label(
                text=f"[b]Course:[/b] {subject['course_name']}",
                font_size='16sp',
                markup=True,
                color=get_color_from_hex('#000000'),
                size_hint_y=None,
                height=dp(20)
            ))
            subject_box.add_widget(Label(
                text=f"[b]Time:[/b] {subject['start_time']} - {subject['end_time']}",
                font_size='14sp',
                markup=True,
                color=get_color_from_hex('#000000'),
                size_hint_y=None,
                height=dp(20)
            ))
            subject_box.add_widget(Label(
                text=f"[b]Classroom:[/b] {subject['classroom']}",
                font_size='14sp',
                markup=True,
                color=get_color_from_hex('#000000'),
                size_hint_y=None,
                height=dp(20)
            ))
            subject_box.add_widget(Label(
                text=f"[b]Day:[/b] {subject['day']}",
                font_size='14sp',
                markup=True,
                color=get_color_from_hex('#000000'),
                size_hint_y=None,
                height=dp(20)
            ))
            container.add_widget(subject_box)


Factory.register('StudentOverlay', cls = StudentOverlay)
Factory.register('TeacherOverlay', cls = TeacherOverlay)
Factory.register('MenuOverlay', cls = MenuOverlay)
Factory.register('MenuOverlay2', cls = MenuOverlay2)

try:
    Builder.load_file('classease.kv')
except Exception as e:
    print(f"KV file load error: {e}")

class ClassEaseApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.teacher_id = None
        self.student_id = None
        
    def build(self):
        self.student_overlay = StudentOverlay()  
        self.teacher_overlay = TeacherOverlay()
        self.menu_overlay = MenuOverlay()
        self.menu_overlay2 = MenuOverlay2()
        self.timetable = Timetable()
        
        sm = ScreenManager()
        sm.add_widget(WelcomeScreen(name = 'welcome'))
        sm.add_widget(LoginScreen(name = 'login'))
        sm.add_widget(MainScreen(name = 'mainsc'))
        sm.add_widget(MainScreen2(name = 'mainsc2'))
        sm.add_widget(MapScreen(name = 'map'))
        sm.add_widget(Timetable(name = 'timetable'))
        sm.add_widget(MondayScreen(name = 'Smonday'))
        sm.add_widget(TuesdayScreen(name = 'Stuesday'))
        sm.add_widget(WednesdayScreen(name = 'Swednesday'))
        sm.add_widget(ThursdayScreen(name = 'Sthursday'))
        sm.add_widget(FridayScreen(name = 'Sfriday'))
        sm.add_widget(Statistics(name = 'statistics'))
        sm.add_widget(Notes(name = 'notes'))
        sm.add_widget(TeacherUploadScreen(name = 'upload'))
        sm.add_widget(TeacherSchedule(name='teacherschedule'))
        return sm
    
    def open_forgot_password_link(self):
        webbrowser.open('https://youtu.be/dQw4w9WgXcQ?si=EBs3gDx_RCqQppuw')
        
    def fetch_notifications(self, student_id=None, limit=5):
        url = f"{API_BASE}/get_notification"
        params = {}
        if student_id:
            params["student_id"] = student_id
        try:
            response = requests.post(url, json=params, timeout=10)
            if response.status_code == 200:
                notifications = response.json().get("notifications", [])
                return notifications[:limit]
            else:
                print("Failed to fetch notifications.")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")
            return []

if __name__ == '__main__':
    ClassEaseApp().run()
 