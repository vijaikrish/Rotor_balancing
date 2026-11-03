import tkinter as tk
import numpy as np
import pytest
from balancing.workbench import Application, number


@pytest.fixture
def app():
    root=tk.Tk()
    root.withdraw()
    a=Application(root)
    yield a
    root.destroy()


def set_entry(e, value):
    e.delete(0,'end')
    e.insert(0,str(value))


def test_trim_uses_actual_not_last_proposal(app):
    p=app.multi
    p.example()
    first=p.solve()
    actual=first.correction_weights*.8
    for v,w in zip(p.actual,actual):
        v.set_complex(w)
    installed=np.array([v.get_complex() for v in p.actual])
    measured=(p.values('baseline').ravel()+p.model@installed).reshape(p.shape[1:])
    for (i,j),w in np.ndenumerate(measured):
        p.vectors['measured',i,j].set_complex(w)
    before=[(v.mag.get(),v.phase.get()) for v in p.actual]
    a=p.trim().correction_weights
    b=p.trim().correction_weights
    np.testing.assert_allclose(a,b)
    assert [(v.mag.get(),v.phase.get()) for v in p.actual]==before
    assert 'NET TOTAL' in p.trim_result.get('1.0','end')
    set_entry(p.rpms[0],3400)
    with pytest.raises(ValueError,match='Solve again'):
        p.trim()


def test_zero_trial_and_singular_rejected(app):
    p=app.single
    p.example()
    set_entry(p.weights[0].mag,0)
    with pytest.raises(ValueError,match='greater than zero'):
        p.solve()
    p.example()
    p.vectors['trial0',0,0].set_complex(p.values('baseline')[0,0])
    with pytest.raises(ValueError):
        p.solve()
    assert p.model is None


@pytest.mark.parametrize('x', ['nan','inf','-1'])
def test_invalid_number(x):
    with pytest.raises(ValueError):
        number(x)


def test_standards_separate_grade_from_measured_criterion(app):
    app.calc_unbalance()
    assert 'NOT a measured vibration limit' in app.u_result.get()
    set_entry(app.limit,2.8)
    set_entry(app.measured,3.0)
    app.compare()
    assert 'Invalid input' in app.v_result.get()
    set_entry(app.source,'Example contract, bearing 1 horizontal')
    app.compare()
    assert 'EXCEEDS' in app.v_result.get()
    assert '3000 r/min' in app.v_result.get()


def test_standards_flexible_requires_rigid_first(app):
    # Flexible-mode calc without a prior rigid U_per calculation must fail
    # clearly, not silently use a stale/zero value.
    assert not hasattr(app,'u_per_rigid')
    app.calc_flexible()
    assert 'Invalid input' in app.flex_result.get()
    assert 'section 1' in app.flex_result.get()


def test_standards_flexible_scales_rigid_u_per(app):
    app.calc_unbalance()  # defaults: G=2.5, N=10000, m=2.5 -> computes self.u_per_rigid
    app.calc_flexible()
    u = app.u_per_rigid
    assert f'{0.60*u:.4f}' in app.flex_result.get()
    assert f'{u:.4f}' in app.flex_result.get()
    assert '60%' in app.flex_result.get()


def test_standards_api_journal_tolerance(app):
    set_entry(app.journal_load,12.5)
    set_entry(app.api_speed,10000)
    app.calc_api()
    expected_si=6350.0*12.5/10000
    assert f'{expected_si:.4f}' in app.api_result.get()
    assert 'this journal' in app.api_result.get()
    set_entry(app.journal_load,0)
    app.calc_api()
    assert 'Invalid input' in app.api_result.get()
