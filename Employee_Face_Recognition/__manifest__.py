{
    'name': 'Face Recognition Attendance',
    'version': '18.0',
    'category': 'Human Resources',
    'summary': 'Face Matching Attendance App',
    'description': """Face Matching Attendance App""",
    'author' : "Ankit",
    'depends': ['hr', 'hr_attendance','base'],
    'license': 'LGPL-3',
    'data': [
        'views/face_attendance.xml',
         'security/ir.model.access.csv',
    ],
    "assets": {
        "web.assets_backend": [
            "Employee_Face_Recognition/static/src/js/webcam_dialog.js",
            "Employee_Face_Recognition/static/src/js/image_field.js",
            "Employee_Face_Recognition/static/src/xml/web_widget_image_webcam.xml",
        ],
    },
    'installable': True,
    'images': ['static/description/icon.jpeg'],
    'auto_install':False,
}
