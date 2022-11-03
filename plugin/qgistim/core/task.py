import abc

from qgis.core import Qgis, QgsTask


class BaseServerTask(QgsTask):
    def __init__(self, parent, data, message_bar):
        super().__init__(self.task_description, QgsTask.CanCancel)
        self.parent = parent
        self.data = data
        self.message_bar = message_bar
        self.response = None
        self.exception = None

    def run(self):
        try:
            self.response = self.parent.parent.execute(self.data)
            if self.response["success"]:
                return True
            else:
                return False
        except Exception as exception:
            self.exception = exception
            return False

    @abc.abstractproperty
    def task_description(self):
        return

    @abc.abstractmethod
    def success_message(self):
        return

    def push_success_message(self) -> None:
        self.message_bar.pushMessage(
            title="Info",
            text=self.success_message(),
            level=Qgis.Info,
        )
        return

    def push_failure_message(self) -> None:
        if self.exception is not None:
            message = "Exception: " + str(self.exception)
        elif self.response is not None:
            message = "Response: " + self.response["message"]
        else:
            message = "Unknown failure"

        self.message_bar.pushMessage(
            title="Error",
            text=f"Failed {self.task_description}. Server error:\n{message}",
            level=Qgis.Critical,
        )
        return

    def finished(self, result) -> None:
        self.parent.set_interpreter_interaction(True)
        # Do not show a success message by default.
        if not result:
            self.push_failure_message()
        return

    def cancel(self) -> None:
        self.parent.set_interpreter_interaction(True)
        self.parent.shutdown_server()
        super().cancel()
        return
