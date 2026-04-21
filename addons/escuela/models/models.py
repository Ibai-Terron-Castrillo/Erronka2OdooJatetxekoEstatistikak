# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Profesor(models.Model):
    _name = "escuela.profesor"
    _description = "Profesor"

    name = fields.Char(string="Nombre", required=True)
    fotografia = fields.Binary(string="Fotografía")
    description = fields.Text(string="Descripción")
    edad = fields.Integer(string="Edad", required=True)
    fecha_nacimiento = fields.Date(string="Fecha de Nacimiento")
    saldo = fields.Float(string="Saldo")
    estado = fields.Boolean(string="Estado del Profesor", default=True)
    grado = fields.Selection(
        [
            ("primaria", "Primaria"),
            ("secundaria", "Secundaria"),
            ("superior", "Superior"),
        ],
        string="Grado",
        default="primaria",
        required=True,
    )
    alumno = fields.One2many("escuela.alumno", inverse_name="profesor", string="Alumnos")
    materia = fields.Many2many(
        comodel_name="escuela.materia",
        relation_name="escuelas_materias",
        column1="escuela_id",
        column2="materia_id",
    )


class Alumno(models.Model):
    _name = "escuela.alumno"
    _description = "Alumno"
    name = fields.Char(string="Nombre", required=True)
    profesor = fields.Many2one("escuela.profesor")
    notas_id = fields.One2many("escuela.nota", inverse_name="alumno_id", string="Notas")

class Materia(models.Model):
    _name = "escuela.materia"
    _description = "Materia"
    name = fields.Char(string="Nombre", required=True)
    profesor = fields.Many2many(
        comodel_name="escuela.profesor",
        relation_name="escuelas_materias",
        column1="materia_id",
        column2="escuela_id",
    )
    notas_ids = fields.One2many("escuela.nota", inverse_name="materia_id", string="Notas")
    alumno_ids = fields.Many2many("escuela.alumno", string="Alumnos", compute="_compute_alumno_ids")
    
    @api.depends("notas_ids", "notas_ids.alumno_id")
    def _compute_alumno_ids(self):
        for materia in self:
            materia.alumno_ids = materia.notas_ids.mapped("alumno_id")
            

class Nota(models.Model):
    _name = "escuela.nota"
    _description = "Nota de Alumno en Materia"

    alumno_id = fields.Many2one("escuela.alumno", string="Alumno", required=True)
    materia_id = fields.Many2one("escuela.materia", string="Materia", required=True)
    nota = fields.Float(string="Nota", required=True)
    estado = fields.Char(string="Estado", compute="_compute_estado")
    
    @api.depends("nota")
    def _compute_estado(self):
        for record in self:
            if record.nota >= 60:
                record.estado = "Ganado"
            else:
                record.estado = "Perdido"