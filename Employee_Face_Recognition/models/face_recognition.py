from odoo import models, fields, api
import face_recognition
import base64
from PIL import Image
import io
import numpy as np
from odoo.exceptions import ValidationError

class FaceMatch(models.Model):
    _name = 'hr.face.recognition'
    _description = 'Face Recognition for HR Employees'

    name = fields.Char("Face Match Name", related='employee_id.name', required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    face_image = fields.Image("Captured Face Image")
    face_encoding = fields.Binary("Captured Face Encoding")
    match_status = fields.Selection([('pending', 'Pending'),
                                     ('matched', 'Matched'),
                                     ('not_matched', 'Not Matched')],
                                    string="Match Status", default='pending')

    def create(self, vals):
        """Generate face encoding upon creation."""
        match = self.match_image_with_employee(vals['face_image'],vals['employee_id'])
        if match:
            vals['match_status'] = 'matched'
        else:
            vals['match_status'] = 'not_matched'

        return super(FaceMatch, self).create(vals)

    def match_image_with_employee(self, img, emp_id):
        try:
            binary_image1 = img
            image_data1 = base64.b64decode(binary_image1)
            image1 = Image.open(io.BytesIO(image_data1))
            image_array1 = np.array(image1)
            face_encoding1 = face_recognition.face_encodings(image_array1)
            if not face_encoding1:
                raise ValidationError('Face not Detected Correctly Please re-take image')
            emps = self.env["hr.employee"].browse(emp_id)
            if not emps.image_1024:
                raise ValidationError("Employee Don't Have an Image Uploaded")
            for emp in emps:
                binary_image2 = emp.image_1024
                image_data2 = base64.b64decode(binary_image2)
                image2 = Image.open(io.BytesIO(image_data2))
                image_array2 = np.array(image2)
                face_encoding2 = face_recognition.face_encodings(image_array2)

                if face_encoding1 and face_encoding2:
                    matches = face_recognition.compare_faces([face_encoding1[0]], face_encoding2[0])
                    if matches[0]:
                        return True
                    else:
                        return False
        except Exception as e:
            if type(e) == ValidationError:
                raise ValidationError(e.name)
            raise ValidationError(e)
        return True