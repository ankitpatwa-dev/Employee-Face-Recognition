/** @odoo-module **/

import { ImageField } from '@web/views/fields/image/image_field';
import { useService } from "@web/core/utils/hooks";
import { patch } from 'web.utils';
import WebcamDialog from '@Employee_Face_Recognition/js/webcam_dialog';


patch(ImageField.prototype, 'Employee_Face_Recognition', {

    setup() {
        this._super(...arguments);
        this.dialogService = useService("dialog");
    },

    _openRearCamera(ev) {
        this.dialogService.add(WebcamDialog, {
            mode: true,
            onWebcamCallback: (data) => this.onWebcamCallback(data),
        });
    },

    async onWebcamCallback(base64) {
        this.props.update(base64)
    }

})