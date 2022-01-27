import numpy as np
from pyzbar.pyzbar import decode
import apps.attendance.attd_capture as attd
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.utils import IntegrityError
import apps.attendance.forms as atf
import apps.attendance.models as atdm
from .filters import AttendanceFilter
import apps.peoples.utils as putils
from django.views import View
from django.http.request import QueryDict
from django.http import response as rp
import threading
import cv2
from django.views.decorators import gzip
from django.http import StreamingHttpResponse
import logging
logger = logging.getLogger('django')
log = logging.getLogger('__main__')
# Create your views here.


class Attendance(LoginRequiredMixin, View):
    params = {
        'form_class': atf.AttendanceForm,
        'template_form': 'attendance/partials/partial_attendance_form.html',
        'template_list': 'attendance/attendance.html',
        'partial_form': 'attendance/partials/partial_attendance_form.html',
        'partial_list': 'attendance/partials/partial_attendance_list.html',
        'related': ['peopleid', 'clientid', 'buid', 'verifiedby', 'gfid'],
        'model': atdm.PeopleEventlog,
        'filter': AttendanceFilter,
        'fields': ['id', 'peopleid__peoplename', 'verifiedby__peoplename', 'peventtype', 'buid__buname', 'datefor',
                   'punch_intime', 'punch_outtime', 'facerecognition', 'gpslocation_in', 'gpslocation_out', 'shift__shiftname']}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # return attendance_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "attd_list", 'filt_name': "attd_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.select_related(
                *self.params['related']).values(*self.params['fields'])
            resp = putils.render_grid(
                request, self.params, "attendance_view", objs)

        # return attemdance_form empty
        elif R.get('action', None) == 'form':
            cxt = {'attd_form': self.params['form_class'](),
                   'msg': "create attendance requested"}
            resp = putils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = putils.render_form_for_delete(request, self.params)
        # return form with instance
        elif R.get('id', None):
            resp = putils.render_form_for_update(
                request, self.params, "attd_form")
        print(f'return resp={resp}')
        return resp

    def post(self, request, *args, **kwargs):
        resp = None
        try:
            print(request.POST)
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            if pk:
                msg = "attendance_view"
                form = putils.get_instance_for_update(
                    data, self.params, msg, int(pk))
            else:
                form = self.params['form_class'](data)
            if form.is_valid():
                resp = self.handle_valid_form(form, request)
            else:
                cxt = {'errors': form.errors}
                resp = putils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = putils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request):
        logger.info('attendance form is valid')
        try:
            import json
            attd = form.save()
            putils.save_userinfo(attd, request.user, request.session)
            logger.info("attendance form saved")
            data = {'success': "Record has been saved successfully",
                    'type': attd.peventtype}
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return putils.handle_intergrity_error('Attendance')


def face_recognition(request):
    log.debug("face_recognition view initaited")
    res = None
    if request.method == 'POST':
        return
    else:
        import cv2
        from pyzbar.pyzbar import decode
        import numpy as np
        from django.conf.urls.static import static
        import time

        if request.GET.get('detectQR'):
            log.debug("request for qr detection")
            # QRcode detection
            res = attd.detect_QR(cv2, decode, np, time)
        elif request.GET.get('detectFace'):
            log.debug("request for fr detection")
            res = attd.recognize_face(cv2, np, time, request.GET.get('code'))
    return res


class VideoCamera(object):
    def __init__(self):
        log.debug('open cam requeted')
        from .attd_capture import try_camera
        self.video = try_camera(cv2)
        if hasattr(self.video, "isOpened") and self.video.isOpened():
            log.debug("camera is opened")
            (self.grabbed, self.frame) = self.video.read()
            threading.Thread(target=self.update, args=()).start()

    def __del__(self):
        self.video.release()

    def get_frame(self):
        image = self.frame
        _, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()

    def update(self):
        while True:
            (self.grabbed, self.frame) = self.video.read()
            detected = self.decode_qr(self.frame)
            if detected:
                self.__del__()

    def decode_qr(self, img):
        log.debug("trying to detect qr")
        for barcode in decode(img):
            print(barcode.data)
            code = barcode.data.decode('utf-8')
            print(code)
            pts = np.array([barcode.polygon], np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(img, [pts], True, [0, 255, 0], 3)
            pts2 = barcode.rect
            cv2.putText(img, code, (pts2[0], pts2[1]), cv2.FONT_HERSHEY_COMPLEX,
                        0.9, (255, 0, 0), 2)
            log.debug("QR is detected")
            return True


def gen(camera):
    while True:
        frame = camera.get_frame()
        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


@gzip.gzip_page
def face_recognition2(request):
    try:
        #cam = VideoCamera()
        return StreamingHttpResponse(gen(cam), content_type="multipart/x-mixed-replace;boundary=frame")
    except:  # This is bad! replace it with proper handling
        pass
