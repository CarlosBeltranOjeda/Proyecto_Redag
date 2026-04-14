-- =====================================================
-- SISTEMA REDAG - Setup de tablas en Supabase
-- Ejecutar en SQL Editor de Supabase
-- =====================================================

-- Sedes
CREATE TABLE IF NOT EXISTS redag_sedes (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    direccion TEXT DEFAULT '',
    activa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO redag_sedes(nombre,direccion) VALUES
    ('Villa Adela','Villa Adela Paraiso'),
    ('Villa Bolivar','Villa Bolivar'),
    ('Amor de Dios','Amor de Dios')
ON CONFLICT DO NOTHING;

-- Jugadores
CREATE TABLE IF NOT EXISTS redag_jugadores (
    id SERIAL PRIMARY KEY,
    nombres TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    edad INTEGER,
    ci TEXT DEFAULT '',
    categoria TEXT,
    estado TEXT DEFAULT 'Nuevo',
    celular TEXT DEFAULT '',
    sede_id INTEGER REFERENCES redag_sedes(id),
    foto_url TEXT DEFAULT '',
    fecha_reg TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pagos
CREATE TABLE IF NOT EXISTS redag_pagos (
    id SERIAL PRIMARY KEY,
    jugador_id INTEGER REFERENCES redag_jugadores(id) ON DELETE CASCADE,
    mes TEXT,
    anio INTEGER,
    matricula NUMERIC DEFAULT 0,
    mensualidad NUMERIC DEFAULT 0,
    dia_pago INTEGER,
    fecha_pago TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Torneos
CREATE TABLE IF NOT EXISTS redag_torneos (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    fecha_inicio TEXT,
    fecha_fin TEXT,
    sede TEXT DEFAULT '',
    descripcion TEXT DEFAULT '',
    estado TEXT DEFAULT 'Planificado',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Jugadores inscritos en torneos
CREATE TABLE IF NOT EXISTS redag_torneo_jugadores (
    id SERIAL PRIMARY KEY,
    torneo_id INTEGER REFERENCES redag_torneos(id) ON DELETE CASCADE,
    jugador_id INTEGER REFERENCES redag_jugadores(id) ON DELETE CASCADE,
    categoria_torneo TEXT,
    fecha_inscripcion TEXT DEFAULT CURRENT_DATE::TEXT,
    UNIQUE(torneo_id, jugador_id)
);

-- =====================================================
-- PERMISOS (Row Level Security)
-- =====================================================
ALTER TABLE redag_sedes ENABLE ROW LEVEL SECURITY;
ALTER TABLE redag_jugadores ENABLE ROW LEVEL SECURITY;
ALTER TABLE redag_pagos ENABLE ROW LEVEL SECURITY;
ALTER TABLE redag_torneos ENABLE ROW LEVEL SECURITY;
ALTER TABLE redag_torneo_jugadores ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "allow_all_sedes" ON redag_sedes;
DROP POLICY IF EXISTS "allow_all_jugadores" ON redag_jugadores;
DROP POLICY IF EXISTS "allow_all_pagos" ON redag_pagos;
DROP POLICY IF EXISTS "allow_all_torneos" ON redag_torneos;
DROP POLICY IF EXISTS "allow_all_torneo_jug" ON redag_torneo_jugadores;

CREATE POLICY "allow_all_sedes" ON redag_sedes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_jugadores" ON redag_jugadores FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_pagos" ON redag_pagos FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_torneos" ON redag_torneos FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "allow_all_torneo_jug" ON redag_torneo_jugadores FOR ALL USING (true) WITH CHECK (true);

-- =====================================================
-- Listo! Las tablas estan creadas.
-- =====================================================
