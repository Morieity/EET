/**
 * Unit tests for the API service layer.
 *
 * Each service should:
 *   - call fetch() with the documented URL/method/body
 *   - surface non-2xx responses as thrown Error
 *
 * fetch is replaced globally with a Jest mock per test.
 */
import { getFiles, uploadFile, deleteFile, openUploadsFolder } from '../fileApi';
import { sendChatMessage } from '../chatApi';
import {
  getFaultTrees,
  getFaultTree,
  getFaultTreeByConversation,
  updateFaultTree,
  deleteFaultTree,
} from '../faultTreeApi';
import {
  getConversations,
  getConversation,
  deleteConversation,
} from '../conversationApi';

const okJson = (payload, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => payload,
});

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.resetAllMocks();
});

describe('fileApi', () => {
  test('getFiles GETs /api/files and returns JSON', async () => {
    global.fetch.mockResolvedValueOnce(okJson([{ file_name: 'a.pdf' }]));

    const result = await getFiles();

    expect(global.fetch).toHaveBeenCalledWith('/api/files');
    expect(result).toEqual([{ file_name: 'a.pdf' }]);
  });

  test('getFiles throws on non-OK status', async () => {
    global.fetch.mockResolvedValueOnce(okJson({}, 500));
    await expect(getFiles()).rejects.toThrow(/500/);
  });

  test('uploadFile POSTs FormData and accepts 202 Accepted', async () => {
    const fd = new FormData();
    global.fetch.mockResolvedValueOnce(okJson({ file_name: 'x.pdf' }, 202));

    const { data, status } = await uploadFile(fd);

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/files',
      expect.objectContaining({ method: 'POST', body: fd })
    );
    expect(status).toBe(202);
    expect(data).toEqual({ file_name: 'x.pdf' });
  });

  test('uploadFile surfaces backend error message on hard failure', async () => {
    global.fetch.mockResolvedValueOnce(okJson({ error: '不支持的类型' }, 400));
    await expect(uploadFile(new FormData())).rejects.toThrow('不支持的类型');
  });

  test('deleteFile URL-encodes file name', async () => {
    global.fetch.mockResolvedValueOnce(okJson({}, 200));
    await deleteFile('我的 文档.pdf');
    expect(global.fetch).toHaveBeenCalledWith(
      `/api/files/${encodeURIComponent('我的 文档.pdf')}`,
      { method: 'DELETE' }
    );
  });

  test('openUploadsFolder POSTs to /api/files/open-folder', async () => {
    global.fetch.mockResolvedValueOnce(okJson({ ok: true }));
    await openUploadsFolder();
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/files/open-folder',
      { method: 'POST' }
    );
  });
});

describe('chatApi', () => {
  test('sendChatMessage POSTs question only when no conversationId', async () => {
    const fakeResp = okJson({});
    global.fetch.mockResolvedValueOnce(fakeResp);

    await sendChatMessage('你好');

    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe('/api/chat');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ question: '你好' });
  });

  test('sendChatMessage includes conversation_id when supplied', async () => {
    global.fetch.mockResolvedValueOnce(okJson({}));
    const ctrl = new AbortController();

    await sendChatMessage('再问一次', 'conv-1', ctrl.signal);

    const [, opts] = global.fetch.mock.calls[0];
    expect(JSON.parse(opts.body)).toEqual({
      question: '再问一次',
      conversation_id: 'conv-1',
    });
    expect(opts.signal).toBe(ctrl.signal);
  });
});

describe('faultTreeApi', () => {
  test('getFaultTrees fetches list', async () => {
    global.fetch.mockResolvedValueOnce(okJson([]));
    await getFaultTrees();
    expect(global.fetch).toHaveBeenCalledWith('/api/fault-trees');
  });

  test('getFaultTree encodes id', async () => {
    global.fetch.mockResolvedValueOnce(okJson({}));
    await getFaultTree('tree/1');
    expect(global.fetch).toHaveBeenCalledWith(
      `/api/fault-trees/${encodeURIComponent('tree/1')}`
    );
  });

  test('getFaultTreeByConversation uses conversation endpoint', async () => {
    global.fetch.mockResolvedValueOnce(okJson({}));
    await getFaultTreeByConversation('conv-1');
    expect(global.fetch).toHaveBeenCalledWith(
      `/api/fault-trees/conversation/${encodeURIComponent('conv-1')}`
    );
  });

  test('updateFaultTree PUTs JSON payload', async () => {
    global.fetch.mockResolvedValueOnce(okJson({ id: 't1' }));
    await updateFaultTree('t1', { name: 'X' });
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe(`/api/fault-trees/${encodeURIComponent('t1')}`);
    expect(opts.method).toBe('PUT');
    expect(opts.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(opts.body)).toEqual({ name: 'X' });
  });

  test('updateFaultTree surfaces backend error message', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ error: '不允许空树' }),
    });
    await expect(updateFaultTree('t1', {})).rejects.toThrow('不允许空树');
  });

  test('deleteFaultTree DELETEs encoded id', async () => {
    global.fetch.mockResolvedValueOnce(okJson({}));
    await deleteFaultTree('t1');
    expect(global.fetch).toHaveBeenCalledWith(
      `/api/fault-trees/${encodeURIComponent('t1')}`,
      { method: 'DELETE' }
    );
  });
});

describe('conversationApi', () => {
  test('getConversations fetches list', async () => {
    global.fetch.mockResolvedValueOnce(okJson([]));
    await getConversations();
    expect(global.fetch).toHaveBeenCalledWith('/api/conversations');
  });

  test('getConversation encodes id', async () => {
    global.fetch.mockResolvedValueOnce(okJson({}));
    await getConversation('c 1');
    expect(global.fetch).toHaveBeenCalledWith(
      `/api/conversations/${encodeURIComponent('c 1')}`
    );
  });

  test('deleteConversation throws on non-OK', async () => {
    global.fetch.mockResolvedValueOnce(okJson({}, 404));
    await expect(deleteConversation('c1')).rejects.toThrow(/404/);
  });
});
