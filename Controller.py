from Main_Window import MainWindow
from Model import Model


class Controller:
    """
    Connects the Model and the View.
    """

    def __init__(self, model: Model, view: MainWindow):
        self.model = model
        self.view = view

        # Display the numbers of invoices on left panel in View
        self.view.update_left_section((self.model.get_succeed_invoices(), self.model.get_funding_requested_invoices(),
                                      self.model.get_failed_invoices()))

        # When new todo_invoice is typed, update the model
        self.view.middle_widget.todoInvoiceUpdateRequest.connect(self.model.add_todo_invoice)
        # When Process All button is clicked, request the model to process
        self.view.todoInvoicesProcessRequest.connect(self.model.process_all_todo_invoices)
        # When Save button is clicked, request the model to save
        self.view.todoInvoicesSaveRequest.connect(self.model.save_todo_invoices_in_excel)
        # When vendor name is dropped into account text bar, update the model
        self.view.middle_widget.dropTextChanged.connect(self.model.update_todo_invoice)
        # When todo_invoice is deleted from View, request Model to delete it as well
        self.view.middle_widget.textBarDeleted.connect(self.model.delete_todo_invoice)
        # When state of checkbox of todo_invoice in View, request Model to update it as well
        self.view.middle_widget.checkboxStateChanged.connect(self.model.update_invoice_checkbox_state)
        # Left section update required signal, request Model to return data
        self.view.left_section_update_required.connect(self.model.send_left_section_data)
        # When the Left section data is ready, update left section in View
        self.model.left_section_data_ready.connect(self.view.update_left_section)
        # When the invoice data in Model changed, refresh in View
        self.model.todoInvoicesChanged.connect(self.on_model_changed)
        #

        # Read todoinvoices from Excel, and display on View
        self.model.read_todo_invoices_from_excel()


    def on_model_changed(self):
        self.view.middle_widget.clear_text_bars_in_view()
        for pair in self.model.get_todo_invoices():
            self.view.middle_widget.add_text_bar_from_model(pair[0], pair[1][0], pair[1][1])

    def show_notification(self, message):
        self.view.middle_widget.expand_notification(message)

