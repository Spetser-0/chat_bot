import { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { api } from '../lib/api';
import {
  Copy,
  Check,
  Trash2,
  Edit2,
  Plus,
  Key,
  Eye,
  EyeOff,
  RotateCcw,
  Sparkles,
  Sliders,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  system_prompt: string | null;
  max_credits_per_day: number | null;
  allowed_skills: string | null;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  total_requests: number;
}

export function DeveloperPage() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [isLoadingKeys, setIsLoadingKeys] = useState(true);

  // Settings state (Feature 5)
  const [defaultCredits, setDefaultCredits] = useState('300');
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [editingKey, setEditingKey] = useState<APIKey | null>(null);
  const [newKey, setNewKey] = useState('');
  const [copied, setCopied] = useState(false);

  // Form states
  const [name, setName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [maxCredits, setMaxCredits] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchKeys = async () => {
    try {
      const response = await api.get('/developer/api-keys');
      setApiKeys(response.data);
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
    } finally {
      setIsLoadingKeys(false);
    }
  };

  useEffect(() => {
    let ignore = false;

    api.get('/developer/api-keys')
      .then((response) => {
        if (!ignore) {
          setApiKeys(response.data);
          setIsLoadingKeys(false);
        }
      })
      .catch((error) => {
        console.error('Failed to fetch API keys:', error);
        if (!ignore) {
          setIsLoadingKeys(false);
        }
      });

    api.get('/admin/settings')
      .then((response) => {
        if (!ignore) {
          setDefaultCredits(String(response.data.default_new_user_credits));
          setIsLoadingSettings(false);
        }
      })
      .catch((error) => {
        console.error('Failed to fetch system settings:', error);
        if (!ignore) {
          setIsLoadingSettings(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  const handleUpdateSettings = async () => {
    const creditsNum = parseInt(defaultCredits, 10);
    if (isNaN(creditsNum) || creditsNum < 0) {
      setSettingsMessage({ type: 'error', text: 'يرجى إدخال رقم صحيح موجب للرصيد.' });
      return;
    }

    try {
      setIsSavingSettings(true);
      setSettingsMessage(null);
      await api.patch('/admin/settings', {
        default_new_user_credits: creditsNum,
      });
      setSettingsMessage({ type: 'success', text: 'تم حفظ إعدادات الرصيد الافتراضي بنجاح.' });
    } catch (error) {
      console.error('Failed to update settings:', error);
      setSettingsMessage({ type: 'error', text: 'حدث خطأ أثناء حفظ الإعدادات.' });
    } finally {
      setIsSavingSettings(false);
    }
  };

  const openCreateModal = () => {
    setName('');
    setSystemPrompt('');
    setMaxCredits('');
    setFormError(null);
    setShowCreateModal(true);
  };

  const openEditModal = (key: APIKey) => {
    setEditingKey(key);
    setName(key.name);
    setSystemPrompt(key.system_prompt || '');
    setMaxCredits(key.max_credits_per_day ? String(key.max_credits_per_day) : '');
    setFormError(null);
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      setFormError('اسم المفتاح مطلوب.');
      return;
    }

    try {
      setIsSubmitting(true);
      setFormError(null);
      const response = await api.post('/developer/api-keys', {
        name: name.trim(),
        system_prompt: systemPrompt.trim() || null,
        max_credits_per_day: maxCredits ? parseInt(maxCredits, 10) : null,
      });

      setNewKey(response.data.plain_key);
      setShowCreateModal(false);
      setShowKeyModal(true);
      fetchKeys();
    } catch (error: any) {
      console.error('Failed to create key:', error);
      setFormError(error?.response?.data?.detail || 'حدث خطأ أثناء إنشاء المفتاح.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!editingKey) return;
    if (!name.trim()) {
      setFormError('اسم المفتاح مطلوب.');
      return;
    }

    try {
      setIsSubmitting(true);
      setFormError(null);
      await api.patch(`/developer/api-keys/${editingKey.id}`, {
        name: name.trim(),
        system_prompt: systemPrompt.trim() || null,
        max_credits_per_day: maxCredits ? parseInt(maxCredits, 10) : null,
      });

      setEditingKey(null);
      fetchKeys();
    } catch (error: any) {
      console.error('Failed to update key:', error);
      setFormError(error?.response?.data?.detail || 'حدث خطأ أثناء تحديث المفتاح.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (keyId: string) => {
    if (!window.confirm('هل أنت متأكد من رغبتك في حذف هذا المفتاح نهائياً؟')) return;

    try {
      await api.delete(`/developer/api-keys/${keyId}`);
      fetchKeys();
    } catch (error) {
      console.error('Failed to delete key:', error);
    }
  };

  const handleToggleActive = async (key: APIKey) => {
    try {
      await api.patch(`/developer/api-keys/${key.id}`, {
        is_active: !key.is_active,
      });
      fetchKeys();
    } catch (error) {
      console.error('Failed to update key status:', error);
    }
  };

  const handleRegenerate = async (key: APIKey) => {
    if (
      !window.confirm(
        `هل أنت متأكد من إعادة توليد المفتاح "${key.name}"؟ سيتم تعطيل المفتاح القديم فوراً.`
      )
    ) {
      return;
    }

    try {
      const response = await api.post(`/developer/api-keys/${key.id}/regenerate`);
      setNewKey(response.data.plain_key);
      setShowKeyModal(true);
      fetchKeys();
    } catch (error) {
      console.error('Failed to regenerate key:', error);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      console.error('Failed to copy to clipboard', err);
    }
  };

  return (
    <div className="developer-page" dir="rtl">
      {/* Header */}
      <div className="developer-page__header">
        <div className="developer-page__title-group">
          <h1>لوحة المطورين</h1>
          <p>إدارة مفاتيح API، وتخصيص الأوامر (System Prompts)، والتحكم في إعدادات النظام.</p>
        </div>
        <Button variant="primary" onClick={openCreateModal}>
          <Plus size={18} />
          <span>إضافة مفتاح جديد</span>
        </Button>
      </div>

      {/* Feature 5: Default Credits Control */}
      <section className="settings-card">
        <div className="settings-card__header">
          <Sliders size={20} className="text-secondary" />
          <div>
            <h2 className="settings-card__title">إعدادات الحسابات الجديدة والكريدت الافتراضي</h2>
            <p className="settings-card__desc">
              حدد رصيد الكريدت التلقائي الذي يحصل عليه كل طالب جديد فور تسجيل حسابه.
            </p>
          </div>
        </div>

        <div className="settings-card__form">
          <Input
            label="الرصيد الافتراضي للحساب الجديد (كريدت)"
            type="number"
            min="0"
            value={defaultCredits}
            onChange={(e) => setDefaultCredits(e.target.value)}
            disabled={isLoadingSettings || isSavingSettings}
          />
          <Button
            variant="secondary"
            onClick={handleUpdateSettings}
            isLoading={isSavingSettings}
            disabled={isLoadingSettings}
          >
            حفظ الإعدادات
          </Button>
        </div>

        {settingsMessage && (
          <div
            className={`alert ${
              settingsMessage.type === 'success' ? 'alert--success' : 'alert--error'
            }`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '13px',
              background: settingsMessage.type === 'success' ? '#f6ffed' : '#fff2f0',
              border: `1px solid ${settingsMessage.type === 'success' ? '#b7eb8f' : '#ffccc7'}`,
              color: settingsMessage.type === 'success' ? '#389e0d' : '#cf1322',
            }}
          >
            {settingsMessage.type === 'success' ? (
              <CheckCircle size={16} />
            ) : (
              <AlertCircle size={16} />
            )}
            <span>{settingsMessage.text}</span>
          </div>
        )}
      </section>

      {/* Feature 4: API Keys List */}
      <section>
        <div style={{ marginBottom: '16px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-ink)' }}>
            مفاتيح API المخصصة ({apiKeys.length})
          </h2>
        </div>

        {isLoadingKeys ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--color-ash)' }}>
            جارٍ تحميل المفاتيح...
          </div>
        ) : apiKeys.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '48px',
              background: 'var(--color-surface)',
              borderRadius: '12px',
              border: '1px dashed var(--color-border)',
            }}
          >
            <Key size={36} style={{ color: 'var(--color-ash)', marginBottom: '12px' }} />
            <h3 style={{ fontSize: '16px', color: 'var(--color-ink)', marginBottom: '8px' }}>
              لا توجد أي مفاتيح API حتى الآن
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--color-graphite)', marginBottom: '16px' }}>
              أنشئ مفتاحك الأول لدمج التطبيقات الخارجية وتخصيص System Prompts المحددة.
            </p>
            <Button variant="primary" onClick={openCreateModal}>
              <Plus size={16} />
              <span>إنشاء مفتاح جديد</span>
            </Button>
          </div>
        ) : (
          <div className="developer-page__keys-grid">
            {apiKeys.map((key) => (
              <div key={key.id} className="api-key-card">
                <div className="api-key-card__header">
                  <div className="api-key-card__title-row">
                    <Key size={18} className="api-key-card__icon" />
                    <span className="api-key-card__name" title={key.name}>
                      {key.name}
                    </span>
                  </div>
                  <span
                    className={`api-key-card__status ${
                      key.is_active
                        ? 'api-key-card__status--active'
                        : 'api-key-card__status--inactive'
                    }`}
                  >
                    {key.is_active ? 'نشط' : 'معطل'}
                  </span>
                </div>

                <div className="api-key-card__prefix">
                  <code>{key.key_prefix}••••••••••••</code>
                </div>

                {key.system_prompt ? (
                  <div className="api-key-card__prompt">
                    <p className="api-key-card__prompt-label">الأوامر المخصصة (System Prompt):</p>
                    <p className="api-key-card__prompt-text">{key.system_prompt}</p>
                  </div>
                ) : (
                  <div className="api-key-card__prompt" style={{ opacity: 0.6 }}>
                    <p className="api-key-card__prompt-label">الأوامر المخصصة:</p>
                    <p className="api-key-card__prompt-text">الوضع الافتراضي (بدون تخصيص)</p>
                  </div>
                )}

                <div className="api-key-card__stats">
                  <span>الطلبات: {key.total_requests}</span>
                  <span>
                    الحد اليومي:{' '}
                    {key.max_credits_per_day ? `${key.max_credits_per_day} كريدت` : 'غير محدود'}
                  </span>
                </div>

                <div className="api-key-card__actions">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => openEditModal(key)}
                    title="تعديل الإعدادات"
                  >
                    <Edit2 size={15} />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleToggleActive(key)}
                    title={key.is_active ? 'تعطيل المفتاح' : 'تفعيل المفتاح'}
                  >
                    {key.is_active ? <EyeOff size={15} /> : <Eye size={15} />}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleRegenerate(key)}
                    title="إعادة توليد الرمز"
                  >
                    <RotateCcw size={15} />
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => handleDelete(key.id)}
                    title="حذف المفتاح"
                  >
                    <Trash2 size={15} />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Modal: Create Key */}
      {showCreateModal && (
        <Modal onClose={() => setShowCreateModal(false)} title="إنشاء مفتاح API جديد">
          <div className="modal-form">
            <Input
              label="اسم المفتاح *"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="مثال: تطبيق الجوال، أو روبوت التليجرام"
              required
            />

            <div className="modal-form__field">
              <label>الأوامر المخصصة (System Prompt)</label>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={4}
                placeholder="أنت مساعد تعليمي متخصص في الرياضيات والإحصاء للجامعيين..."
              />
            </div>

            <Input
              label="الحد الأقصى للكريدت اليومي (اختياري)"
              type="number"
              min="0"
              value={maxCredits}
              onChange={(e) => setMaxCredits(e.target.value)}
              placeholder="اتركه فارغاً للاستخدام غير المحدود"
            />

            {formError && (
              <div
                style={{
                  color: '#cf1322',
                  fontSize: '13px',
                  background: '#fff2f0',
                  padding: '6px 10px',
                  borderRadius: '4px',
                }}
              >
                {formError}
              </div>
            )}

            <div className="modal-form__actions">
              <Button
                variant="ghost"
                onClick={() => setShowCreateModal(false)}
                disabled={isSubmitting}
              >
                إلغاء
              </Button>
              <Button variant="primary" onClick={handleCreate} isLoading={isSubmitting}>
                <Sparkles size={16} />
                <span>إنشاء المفتاح</span>
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Edit Key */}
      {editingKey && (
        <Modal onClose={() => setEditingKey(null)} title="تعديل مفتاح API">
          <div className="modal-form">
            <Input
              label="اسم المفتاح *"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

            <div className="modal-form__field">
              <label>الأوامر المخصصة (System Prompt)</label>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={4}
                placeholder="أدخل الأوامر المخصصة لهذا المفتاح..."
              />
            </div>

            <Input
              label="الحد الأقصى للكريدت اليومي"
              type="number"
              min="0"
              value={maxCredits}
              onChange={(e) => setMaxCredits(e.target.value)}
              placeholder="اتركه فارغاً للاستخدام غير المحدود"
            />

            {formError && (
              <div
                style={{
                  color: '#cf1322',
                  fontSize: '13px',
                  background: '#fff2f0',
                  padding: '6px 10px',
                  borderRadius: '4px',
                }}
              >
                {formError}
              </div>
            )}

            <div className="modal-form__actions">
              <Button
                variant="ghost"
                onClick={() => setEditingKey(null)}
                disabled={isSubmitting}
              >
                إلغاء
              </Button>
              <Button variant="primary" onClick={handleSaveEdit} isLoading={isSubmitting}>
                حفظ التعديلات
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Show Plain Key Once */}
      {showKeyModal && (
        <Modal onClose={() => setShowKeyModal(false)} title="المفتاح الجديد">
          <div className="key-warning">
            ⚠️ <strong>احفظ هذا المفتاح الآن في مكان آمن!</strong>
            <br />
            لن تتمكن من رؤية هذا المفتاح بالكامل مرة أخرى لأسباب أمنية.
          </div>

          <div className="key-display">
            <code>{newKey}</code>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => copyToClipboard(newKey)}
              title="نسخ إلى الحافظة"
            >
              {copied ? <Check size={16} className="text-success" /> : <Copy size={16} />}
            </Button>
          </div>

          {copied && (
            <p style={{ color: '#389e0d', fontSize: '13px', margin: '-8px 0 12px 0' }}>
              ✓ تم نسخ المفتاح إلى الحافظة!
            </p>
          )}

          <Button fullWidth variant="primary" onClick={() => setShowKeyModal(false)}>
            تم الحفظ بنجاح
          </Button>
        </Modal>
      )}
    </div>
  );
}
export default DeveloperPage;
