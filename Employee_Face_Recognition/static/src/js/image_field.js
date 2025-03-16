/** @odoo-module **/

import { ImageField, imageField } from '@web/views/fields/image/image_field';
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import WebcamDialog from '@Employee_Face_Recognition/js/webcam_dialog';


patch(ImageField.prototype, {

    setup() {
        super.setup()
        this.dialogService = useService("dialog");
    },

    _openRearCamera(ev) {
        this.dialogService.add(WebcamDialog, {
            mode: true,
            onWebcamCallback: (data) => this.onWebcamCallback(data),
        });
    },

    async onWebcamCallback(base64) {
        this.props.record.update({[this.props.name]:base64})
    }

})
