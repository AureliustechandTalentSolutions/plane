# ExecuFlow Store Test Specification

## Test Framework Setup Required
- [ ] Install Vitest or Jest for TypeScript/MobX testing
- [ ] Configure test environment for MobX stores
- [ ] Setup mock for ExecuFlowService

## Unit Tests Required (RED Phase)

### Store Initialization
```typescript
describe('ExecuFlowStore', () => {
  describe('Initialization', () => {
    it('should initialize with null activeSession', () => {
      // Arrange & Act
      const store = new ExecuFlowStore(mockRootStore);

      // Assert
      expect(store.activeSession).toBeNull();
    });

    it('should initialize with empty microTasks array', () => {
      const store = new ExecuFlowStore(mockRootStore);
      expect(store.microTasks).toEqual([]);
    });

    it('should initialize with isLoading as false', () => {
      const store = new ExecuFlowStore(mockRootStore);
      expect(store.isLoading).toBe(false);
    });

    it('should initialize with null error', () => {
      const store = new ExecuFlowStore(mockRootStore);
      expect(store.error).toBeNull();
    });
  });

  describe('fetchActiveSession', () => {
    it('should set isLoading to true while fetching', async () => {
      // Arrange
      const store = new ExecuFlowStore(mockRootStore);
      mockService.listFocusSessions.mockResolvedValue([mockSession]);

      // Act
      const promise = store.fetchActiveSession();

      // Assert
      expect(store.isLoading).toBe(true);
      await promise;
    });

    it('should update activeSession when API returns active session', async () => {
      const store = new ExecuFlowStore(mockRootStore);
      const mockSession = { id: '1', is_active: true, session_type: 'pomodoro' };
      mockService.listFocusSessions.mockResolvedValue([mockSession]);

      await store.fetchActiveSession();

      expect(store.activeSession).toEqual(mockSession);
      expect(store.isLoading).toBe(false);
    });

    it('should set activeSession to null when no active session exists', async () => {
      const store = new ExecuFlowStore(mockRootStore);
      mockService.listFocusSessions.mockResolvedValue([]);

      await store.fetchActiveSession();

      expect(store.activeSession).toBeNull();
    });

    it('should set error when API call fails', async () => {
      const store = new ExecuFlowStore(mockRootStore);
      mockService.listFocusSessions.mockRejectedValue(new Error('API Error'));

      await expect(store.fetchActiveSession()).rejects.toThrow();

      expect(store.error).toBe('API Error');
      expect(store.isLoading).toBe(false);
    });
  });

  describe('startFocusSession', () => {
    it('should create new session and set as active', async () => {
      const store = new ExecuFlowStore(mockRootStore);
      const mockSession = { id: '1', session_type: 'deep_work', is_active: true };
      mockService.createFocusSession.mockResolvedValue(mockSession);

      await store.startFocusSession('deep_work');

      expect(store.activeSession).toEqual(mockSession);
      expect(mockService.createFocusSession).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        expect.objectContaining({ session_type: 'deep_work' })
      );
    });

    it('should set error when session creation fails', async () => {
      const store = new ExecuFlowStore(mockRootStore);
      mockService.createFocusSession.mockRejectedValue(new Error('Create failed'));

      await expect(store.startFocusSession('pomodoro')).rejects.toThrow();

      expect(store.error).toBe('Create failed');
    });
  });

  describe('endFocusSession', () => {
    it('should update session and clear activeSession', async () => {
      const store = new ExecuFlowStore(mockRootStore);
      const mockSession = { id: '1', is_active: true };
      store.activeSession = mockSession;
      mockService.updateFocusSession.mockResolvedValue({ ...mockSession, is_active: false });

      await store.endFocusSession();

      expect(store.activeSession).toBeNull();
      expect(mockService.updateFocusSession).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        '1',
        expect.objectContaining({ is_active: false })
      );
    });

    it('should throw error when no active session exists', async () => {
      const store = new ExecuFlowStore(mockRootStore);

      await expect(store.endFocusSession()).rejects.toThrow('No active session');
    });
  });

  describe('fetchMicroTasks', () => {
    it('should fetch and store micro tasks', async () => {
      const store = new ExecuFlowStore(mockRootStore);
      const mockTasks = [
        { id: '1', title: 'Task 1', is_completed: false },
        { id: '2', title: 'Task 2', is_completed: false }
      ];
      mockService.listMicroTasks.mockResolvedValue(mockTasks);

      await store.fetchMicroTasks();

      expect(store.microTasks).toEqual(mockTasks);
    });

    it('should filter incomplete tasks', async () => {
      const store = new ExecuFlowStore(mockRootStore);
      const mockTasks = [
        { id: '1', title: 'Task 1', is_completed: false },
        { id: '2', title: 'Task 2', is_completed: true }
      ];
      mockService.listMicroTasks.mockResolvedValue(mockTasks);

      await store.fetchMicroTasks();

      expect(store.microTasks).toHaveLength(1);
      expect(store.microTasks[0].id).toBe('1');
    });
  });

  describe('computed - completedToday', () => {
    it('should count completed tasks from today', async () => {
      const store = new ExecuFlowStore(mockRootStore);
      const today = new Date().toISOString();
      const mockTasks = [
        { id: '1', is_completed: true, completed_at: today },
        { id: '2', is_completed: true, completed_at: today },
        { id: '3', is_completed: true, completed_at: '2024-01-01' }
      ];
      mockService.listMicroTasks.mockResolvedValue(mockTasks);

      await store.fetchMicroTasks();

      expect(store.completedToday).toBe(2);
    });
  });

  describe('updateEnergyLevel', () => {
    it('should update energy level', () => {
      const store = new ExecuFlowStore(mockRootStore);

      store.updateEnergyLevel('high');

      expect(store.energyLevel).toBe('high');
    });
  });
});
```

## Integration Tests Required

### Store Context Integration
```typescript
describe('ExecuFlowStore Integration', () => {
  it('should be accessible via useExecuFlow hook', () => {
    const { result } = renderHook(() => useExecuFlow(), {
      wrapper: StoreProvider
    });

    expect(result.current).toBeDefined();
    expect(result.current.fetchActiveSession).toBeInstanceOf(Function);
  });
});
```

## Test Coverage Goals
- [ ] 100% coverage for all actions
- [ ] 100% coverage for all computed properties
- [ ] Error handling for all API calls
- [ ] Loading state transitions
- [ ] Optimistic updates with rollback

## Expected Test Results (RED Phase)
All tests listed above should FAIL initially because:
1. ExecuFlowStore class does not exist
2. Store is not added to RootStore
3. useExecuFlow hook does not exist
4. No properties or methods are implemented

This is the RED phase of TDD - tests fail as expected.
