from django.urls import path, reverse
from django.shortcuts import render, redirect
import pandas as pd
import time
from django.http import JsonResponse
from django.contrib import admin, messages
from django.utils.html import format_html
from django import forms

from subjectandmessage.models import SubjectAndMessage
from credentials.models import Credentials
from .models import EmailsData
import smtplib
from django.core.exceptions import ObjectDoesNotExist


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField()
    group = forms.CharField(max_length=50, label="Grupo")

@admin.register(EmailsData)
class EmailsDataAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'group')
    list_filter = ('group',)
    list_per_page = 94


    def mark_as_priority(self, request, queryset):
        """Envía correos a los registros seleccionados respetando el límite de 400 correos diarios."""
        processed_ids = []
        errors = []
        start_time = time.time()

        try:
            credentials = Credentials.objects.filter(is_active=True).first()
            if not credentials:
                self.message_user(request, "No se encontraron credenciales configuradas.", level='error')
                return
            credentials.reset_counter_if_needed()

            if credentials.emails_sent_today > 376:
                self.message_user(request, f"La cuenta {credentials.email_account} alcanzó su límite diario de 8 correos.", level='error')
                return

            name_account = credentials.name_account
            email_account = credentials.email_account
            password_account = credentials.password_account
        except ObjectDoesNotExist:
            self.message_user(request, "No se encontraron credenciales configuradas.", level='error')
            return

        try:
            subject_and_message = SubjectAndMessage.objects.first()
            if not subject_and_message:
                self.message_user(request, "No se encontraron mensajes configurados.", level='error')
                return

            subject = subject_and_message.subject
            message_template = subject_and_message.message
        except ObjectDoesNotExist:
            self.message_user(request, "No se encontraron mensajes configurados.", level='error')
            return

        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login(email_account, password_account)
        except Exception as e:
            self.message_user(request, f"Error al conectarse al servidor SMTP: {e}", level='error')
            return

        for email_data in queryset:
            if credentials.emails_sent_today > 376:
                self.message_user(request, f"Límite diario alcanzado para la cuenta {credentials.email_account}.", level='warning')
                break

            recipient_name = f"{email_data.first_name} {email_data.last_name}"
            recipient_email = email_data.email

            personalized_subject = f"{subject}"
            personalized_message = (
                f"{message_template}\n\n"
            )

            sent_email = (
                f"From: {name_account} <{email_account}>\n"
                f"To: {recipient_name} <{recipient_email}>\n"
                f"Subject: {personalized_subject}\n\n"
                f"{personalized_message}"
            )

            try:

                server.sendmail(email_account, [recipient_email], sent_email.encode('utf-8'))
                time.sleep(2)
                processed_ids.append(email_data.id)  

                credentials.emails_sent_today += 1
                credentials.save()
            except Exception as e:
                errors.append(f"No se pudo enviar el correo a {recipient_email}. Error: {e}")
                self.message_user(request, f"No se pudo enviar el correo a {recipient_email}. Error: {e}", level='error')

        server.close()

        end_time = time.time()  # Finaliza el cronómetro
        total_time = end_time - start_time  # Calcula el tiempo total en segundos
        minutes, seconds = divmod(int(total_time), 60)

        if processed_ids:
            self.message_user(request, f"Correos enviados correctamente: {len(processed_ids)}.", level='success')
        if errors:
            self.message_user(request, f"Errores encontrados: {len(errors)}.", level='warning')
        
        self.message_user(
        request,
        f"Se enviaron {len(processed_ids)} correos y se demoró {minutes} minutos y {seconds} segundos en enviarlos.",
        level='success'
    )

    actions = [mark_as_priority]

    mark_as_priority.short_description = "Enviar correos"


    actions = [mark_as_priority]

    def changelist_view(self, request, extra_context=None):
        """Personaliza la página de lista para incluir un enlace al formulario de carga de Excel."""
        extra_context = extra_context or {}
        extra_context['upload_excel_url'] = reverse('admin:upload_excel')  # Obtén la URL personalizada
        return super().changelist_view(request, extra_context=extra_context)

    def upload_excel(self, request):
        if request.method == "POST":
            form = ExcelUploadForm(request.POST, request.FILES)
            if form.is_valid():
                excel_file = request.FILES['excel_file']
                group = form.cleaned_data['group']  # Obtener el valor del grupo del formulario
                try:
                    # Leer el archivo Excel usando pandas
                    data = pd.read_excel(excel_file)

                    # Iterar sobre las filas y poblar la base de datos
                    for index, row in data.iterrows():
                        email = row['email']

                        # Ignorar correos que contienen un guion bajo
                        if '_' in email:
                            messages.info(request, f"El correo {email} fue ignorado porque contiene un guion bajo (_).")
                            continue

                        # Extraer el nombre y apellido del correo
                        if '@' in email:
                            name_parts = email.split('@')[0].split('.')

                            # Asignar el primer nombre y el apellido
                            first_name = ' '.join(name_parts[:-1]).capitalize()  # Todo antes del último punto
                            last_name = name_parts[-1].capitalize()  # Última palabra

                            # Transformar a mayúsculas
                            first_name = first_name.upper()
                            last_name = last_name.upper()

                            # Crear el registro
                            EmailsData.objects.create(
                                email=email,
                                first_name=first_name,
                                last_name=last_name,
                                group=group,  # Asignar el grupo al registro
                            )
                    messages.success(request, "Los datos del archivo Excel fueron cargados correctamente.")
                    return redirect("..")
                except Exception as e:
                    messages.error(request, f"Error procesando el archivo: {e}")
        else:
            form = ExcelUploadForm()

        context = {
            'form': form,
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        }
        return render(request, "admin/upload_excel.html", context)

    def get_urls(self):
        custom_urls = [
            path('upload-excel/', self.admin_site.admin_view(self.upload_excel), name="upload_excel"),
        ]
        return custom_urls + super().get_urls()